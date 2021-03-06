var colors = ['#ffffff', '#ffffe0','#ffd4ad','#ffa77a','#ff7246','#ff0000'];
var numPrefectures = 34;

var treatmentRanges = ['0 Centers', '1 Center', '2 Centers', '3 Centers', '4 Centers', '5 Centers'];
var populationRanges = ['<150000', '150000-200000', '200000-275000', '275000-295000', '295000-350000', '>350000'];

var population = {'Beyla': 26,
'Boffa': 13,
'Boke': 31,
'Conakry': 34,
'Coyah': 15,
'Dabola': 9,
'Dalaba': 5,
'Dinguiraye': 11,
'Dubreka': 27,
'Faranah': 18,
'Forecariah': 14,
'Fria': 1,
'Gaoual': 10,
'Gueckedou': 22,
'Kankan': 32,
'Kerouane': 12,
'Kindia': 30,
'Kissidougou': 19,
'Koubia': 2,
'Koundara': 4,
'Kouroussa': 16,
'Labe': 24,
'Lelouma': 6,
'Lola': 7,
'Macenta': 23,
'Mali': 21,
'Mamou': 25,
'Mandiana': 28,
'Nzerekore': 29,
'Pita': 17,
'Siguiri': 33,
'Telimele': 20,
'Tougue': 3,
'Yomou': 8};

$(document).ready(function() {
  var state = {
    'isPopulationMap': false,
    'selectedElement': null
  }

  var $treatmentCenters = $('#treatment-centers');

  $('svg').find('path').each(function(index, province) {
    var $province = $(province);
    var id = $province.attr('id');

    state[id] = {}
    state[id]['numTreatmentCenters'] = 0;

    // Attaches event listeners to the path
    $province.click(function() {
      if (state['isPopulationMap']) return;

      state[id]['numTreatmentCenters'] = (state[id]['numTreatmentCenters'] + 1) % colors.length;

      colorProvince($province);

      var elem = document.getElementById('t-' + id);
      var $elem = $(elem); // I'm too lazy to remove the "." from the id to make it compatible with JQuery
      $elem.find('.C').html(state[id]['numTreatmentCenters']);

      if (state['selectedElement']) {
        state['selectedElement'].removeClass('selected')
      }
      $elem.addClass('selected');
      state['selectedElement'] = $elem;
    });

    // Creates the Treatment Center element in table
    $treatmentCenters.append(createRow($province));
    $treatmentCenters.append($('<div></div>').attr('class', 'ui divider'));
  });

  $('#gradient').html(getGradientHTML());

  $('.population-button').click(function() {
    createPopulationMap();
  });

  $('.treatment-button').click(function() {
    createTreatmentMap();
  });

  function colorProvince($province) {
    var index = state[$province.attr('id')]['numTreatmentCenters'];
    $province.attr('fill', colors[(index) % colors.length]);
  }

  function createRow($province) {
    var $row = $('<div></div>').attr('id', 't-' + $province.attr('id'));
    
    var $col1 = $('<div></div>').html($province.attr('data-name')).attr('class', 'A');
    var $col2 = $('<div></div>').html("B").attr('class', 'B');
    var $col3 = $('<div></div>').html(state[$province.attr('id')]['numTreatmentCenters']).attr('class', 'C');

    $row.append($col1);
    $row.append($col2);
    $row.append($col3);

    return $row;
  }

  function getGradientHTML() {
    var html = '';
    for (var i = 0; i < colors.length; i++) {
      html += '<td bgcolor="' + colors[i] + '">&nbsp;' + (state['isPopulationMap'] ? populationRanges[i] : treatmentRanges[i]) + '&nbsp;</td>';
    }
    return html;
  }

  function createPopulationMap() {
    state['isPopulationMap'] = true;
    $('.page-content svg').find('path').each(function(index, province) {
      var name = $(province).attr('data-name');
      var count = population[name];
      $(province).attr('fill', getGradientColor(count));
    });
    $('#gradient').html(getGradientHTML());
  };

  function getGradientColor(count) {
    var intervalSize = numPrefectures / colors.length;
    return colors[Math.floor((count - 1) / intervalSize)];
  }

  function createTreatmentMap() {
    state['isPopulationMap'] = false;
    $('.page-content svg').find('path').each(function(index, province) {
      $(province).attr('index', colorProvince($(province)));
    });
    $('#gradient').html(getGradientHTML());
  }
});
