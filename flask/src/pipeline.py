import tensorflow as tf
import prettytensor as pt
import numpy as np
import scipy.io as io
import argparse
import models
import sys
import os
import data_loader

from collections import defaultdict

from constants import *
from progressbar import ETA, Bar, Percentage, ProgressBar
from sklearn.metrics import precision_recall_curve, average_precision_score

np.random.seed(1234)
tf.set_random_seed(0)

parser = argparse.ArgumentParser(description='Epidemic Response System')
parser.add_argument('-wd', '--working_directory', help='directory for storing logs')
parser.add_argument('-sf', '--save_frequency', help='Number of epochs before saving')
parser.add_argument('--model_path', help='Stored model path')
parser.add_argument('mode', choices=('train', 'eval', 'extrapolate', 'etc_user'), help='train or eval')
args = parser.parse_args()

# Training Constants
learning_rate = 1e-4
batch_size = 1
num_timesteps = 25
num_feats = 3
max_epoch = 601
num_extrapolate = 20
dataset_size = 3069
updates_per_epoch = int(np.ceil(float(dataset_size) / float(batch_size)))

if args.working_directory:
    working_directory = args.working_directory
else:
    working_directory = 'trial/'
if args.save_frequency:
    save_frequency = args.save_frequency
else:
    save_frequency = 10
if args.model_path:
    model_path = args.model_path
else:
    model_path = 'trial/checkpoints/model.ckpt-600'

def get_loss(pred, gt):
    return tf.div(tf.reduce_mean(tf.square(tf.sub(gt, pred))),
                  tf.constant(float(batch_size)))

def train():
    with tf.device('/gpu:0'): # run on specific device
        input_tensor, pred, gt = models.import_model(num_timesteps,
                                                     num_feats,
                                                     batch_size)
        loss = get_loss(pred, gt)
        optimizer = tf.train.AdamOptimizer(learning_rate, epsilon=1.0)
        train = optimizer.minimize(loss=loss)

    dataset = data_loader.read_datasets(PREPROCESSED_DATA)
    saver = tf.train.Saver()  # defaults to saving all variables

    # logging the loss function
    loss_placeholder = tf.placeholder(tf.float32)
    tf.scalar_summary('train_loss', loss_placeholder)

    merged = tf.merge_all_summaries()

    init = tf.initialize_all_variables()

    with tf.Session(config=tf.ConfigProto(allow_soft_placement=True)) as sess:
        writer = tf.train.SummaryWriter(os.path.join(working_directory, 'logs'),
                sess.graph_def)
        sess.run(init)

        for epoch in range(max_epoch):
            training_loss = 0.0

            widgets = ["epoch #%d|" % epoch, Percentage(), Bar(), ETA()]
            pbar = ProgressBar(updates_per_epoch, widgets=widgets)
            pbar.start()
            for i in range(updates_per_epoch):
                pbar.update(i)
                input_batch, gt_batch = dataset.next_batch(batch_size)
                _, loss_value = sess.run([train, loss],
                                         {input_tensor : input_batch,
                                          gt : [gt_batch]})
                training_loss += np.sum(loss_value)

            training_loss = training_loss/(updates_per_epoch)
            print("Loss %f" % training_loss)

            # save model
            if epoch % save_frequency == 0:
                checkpoints_folder = os.path.join(working_directory, 'checkpoints')
                if not os.path.exists(checkpoints_folder):
                    os.makedirs(checkpoints_folder)
                saver.save(sess, os.path.join(checkpoints_folder, 'model.ckpt'),
                           global_step=epoch)

                # save summaries
                summary_str = sess.run(merged,
                              feed_dict={input_tensor : input_batch,
                                         gt : [gt_batch],
                                         loss_placeholder: training_loss})
                writer.add_summary(summary_str, global_step=epoch)
        writer.close()

def evaluate(print_grid=False):
    with tf.device('/gpu:0'): # run on specific device
        input_tensor, pred, gt = models.import_model(num_timesteps,
                                                     num_feats,
                                                     batch_size)

    dataset = data_loader.read_datasets(PREPROCESSED_DATA, dataset_type='test')

    saver = tf.train.Saver()

    with tf.Session(config=tf.ConfigProto(allow_soft_placement=True)) as sess:
        saver.restore(sess, model_path)

        all_pred, all_gt = [], []
        for i in range(updates_per_epoch):
            input_batch, gt_batch = dataset.next_batch(batch_size)
            pred_value = sess.run([pred],
                                  {input_tensor : input_batch,
                                   gt : [gt_batch]})

            all_pred.append(pred_value)
            all_gt.append(gt_batch)

        num_align = 0
        rmse = []
        for i in range(len(all_pred)):
            if all_pred[i] == all_gt[i]: num_align += 1
            rmse.append(np.sqrt(np.power((all_pred[i] - all_gt[i]), 2)))

        print "Accuracy:", float(num_align)/len(all_pred)
        print "Avg. RMSE", np.mean(rmse)
        print "Variance RMSE", np.var(rmse)



def extrapolate(history_file, etc_dict=None):
    # etc_dict is a dict mapping from province to # of new ETCs there
    with tf.device('/gpu:0'):  # run on specific device
        input_tensor, pred, gt = models.import_model(num_timesteps,
                                                     num_feats,
                                                     batch_size)

    # dataset should be [num_provinces x (num_timesteps, num_feats)]
    data, provinces = np.load(history_file)

    saver = tf.train.Saver()

    with tf.Session(config=tf.ConfigProto(allow_soft_placement=True)) as sess:
        saver.restore(sess, model_path)

        all_extrapolated = defaultdict(list)
        all_new_values = defaultdict(list)
        for province, province_data in zip(provinces, data):
            # for one province
            # get lat and lon
            lat, lon = province_data[0, 1:]
            extrapolated = []
            new_values = []
            old_value = province_data[-1, 0]
            for t in range(num_extrapolate):
                pred_value = sess.run([pred],
                                      {input_tensor: province_data})[0][0][0]
                if pred_value < 0:
                    pred_value = 0
                extrapolated.append(pred_value)

                new_value = pred_value
                if etc_dict and province in etc_dict:
                    new_value = old_value + ((pred_value - old_value) * (1/(etc_dict[province] + 3)))
                    # new_value *= (1 - etc_dict[province] * 0.1)
                old_value = pred_value
                new_values.append(new_value)
                new_sample = np.array([new_value, lat, lon])

                new_sample = np.reshape(new_sample, (1, -1))
                province_data = province_data[1:, :]
                province_data = np.concatenate((province_data, new_sample), axis=0)
                # make example with [pred_value, lat, lon]
                # remove first element in input batch and add extrapolated
            all_extrapolated[province] = extrapolated
            all_new_values[province] = new_values


    for i, province in enumerate(provinces):
        print province
        print data[i]
        print all_extrapolated[province]
        print all_new_values[province]
    # np.save('all_extrapolated', all_extrapolated)

    return all_extrapolated


if __name__ == "__main__":
    if args.mode == 'train':
        train()
    elif args.mode == 'eval':
        evaluate(print_grid=False)
    elif args.mode == 'extrapolate':
        extrapolate(PREPROCESSED_GUINEA_DATA_EXTRA)
    elif args.mode == 'etc_user':
        etc_dict = {
            "macenta"   : 2,
            "coyah" : 1,
            "kerouane" : 1
        }
        extrapolate(PREPROCESSED_GUINEA_DATA_EXTRA, etc_dict)
