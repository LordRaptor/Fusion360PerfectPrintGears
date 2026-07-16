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
    } finally {
      setBusy(false);   // always clear the busy state, even on a bad payload
    }
    return '';   // required by the Fusion palette contract
  }
};

document.getElementById('query').addEventListener('submit', function (evt) {
  evt.preventDefault();
  var query = {
    // The engine's ratio is driving/driven = output-speed/input-speed, so the target
    // numerator is the OUTPUT turns and the denominator is the INPUT turns. The dialog
    // asks in input:output order (the natural clock framing), so map accordingly.
    target_num: intVal('ratio_output'),
    target_den: intVal('ratio_input'),
    min_stages: intVal('min_stages'),
    max_stages: intVal('max_stages'),
    teeth_min: intVal('teeth_min'),
    teeth_max: intVal('teeth_max'),
    direction: document.getElementById('direction').value,
    coaxial: document.getElementById('coaxial').checked
  };
  setBusy(true);
  // adsk.fusionSendData is SYNCHRONOUS -- it blocks this thread until the Python search
  // returns, freezing the palette. Defer it past two animation frames so the browser
  // actually paints the busy state (spinner + "Searching…") before the freeze.
  window.requestAnimationFrame(function () {
    window.requestAnimationFrame(function () {
      // Fires palette.incomingFromHTML with action 'search'.
      adsk.fusionSendData('search', JSON.stringify(query));
    });
  });
});

function intVal(id) { return parseInt(document.getElementById(id).value, 10); }

function setBusy(busy) {
  var btn = document.getElementById('search');
  btn.disabled = busy;
  btn.textContent = busy ? 'Searching…' : 'Search';
  document.getElementById('spinner').hidden = !busy;
  if (busy) { showMessage('Searching…', false); }
}

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
    // The engine reports the ratio string as output:input (driving/driven). The UI speaks
    // input:output, so flip the STRING to match the dialog and the user's mental model
    // (e.g. "12 turns in : 1 turn out" for a minutes-to-hours reduction). The decimal is
    // left as the engine's output-per-input value (e.g. 1/12 = 0.0833 — how far the output
    // advances per single input turn), which reads naturally alongside "12 : 1".
    var rp = t.ratio.split(' : ');
    var ratioIO = rp[1] + ' : ' + rp[0];
    var tr = document.createElement('tr');
    [String(i + 1), stages, ratioIO + '  (' + t.ratio_decimal.toFixed(4) + ')',
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
