// palette.js — Gear Train Calculator palette front-end.

// Receive messages from Python: window.fusionJavaScriptHandler.handle(action, data).
window.fusionJavaScriptHandler = {
  handle: function (action, data) {
    try {
      if (action === 'results') {
        render(JSON.parse(data));
      }
    } catch (e) {
      showMessage('Error handling response: ' + e, true);
    }
    return '';   // required by the Fusion palette contract
  }
};

document.getElementById('query').addEventListener('submit', function (evt) {
  evt.preventDefault();
  var query = {
    target_num: intVal('target_num'),
    target_den: intVal('target_den'),
    min_stages: intVal('min_stages'),
    max_stages: intVal('max_stages'),
    teeth_min: intVal('teeth_min'),
    teeth_max: intVal('teeth_max'),
    direction: document.getElementById('direction').value,
    coaxial: document.getElementById('coaxial').checked
  };
  showMessage('Searching…', false);
  // Send to Python -> fires palette.incomingFromHTML with action 'search'.
  adsk.fusionSendData('search', JSON.stringify(query));
});

function intVal(id) { return parseInt(document.getElementById(id).value, 10); }

function showMessage(text, isError) {
  var box = document.getElementById('messages');
  box.textContent = text;
  box.className = isError ? 'error' : '';
}

function render(result) {
  var table = document.getElementById('results');
  var tbody = table.querySelector('tbody');
  tbody.innerHTML = '';

  if (result.error) { showMessage(result.error, true); table.hidden = true; return; }

  var notes = (result.warnings || []).slice();
  if (result.truncated) {
    notes.push('Search was cut short for speed — showing a partial list (up to 200). '
             + 'Narrow the tooth range or stage count to see fewer, more complete results.');
  }

  if (!result.trains.length) {
    showMessage('No exact train found in these limits — widen the range or stage count.', false);
    table.hidden = true;
    if (notes.length) { showMessage(notes.join(' '), false); }
    return;
  }

  result.trains.forEach(function (t, i) {
    var stages = t.stages.map(function (s) { return s.driving + ' ÷ ' + s.driven; }).join(', ');
    var toothSum = (t.coaxial_sum !== null && t.coaxial_sum !== undefined)
      ? String(t.coaxial_sum) + ' (coaxial — use one module)'
      : t.stages.map(function (s) { return s.tooth_sum; }).join(', ');
    var tr = document.createElement('tr');
    [String(i + 1), stages, t.ratio + '  (' + t.ratio_decimal.toFixed(4) + ')',
     String(t.num_gears), t.direction, toothSum].forEach(function (cell) {
      var td = document.createElement('td');
      td.textContent = cell;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  table.hidden = false;
  showMessage(notes.join(' '), false);
}
