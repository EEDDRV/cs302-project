$(function () {
  let selectedFile = null;
  const maxBytes = 5 * 1024 * 1024;
  const allowed = ['image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/bmp'];
  const $input = $('#imageInput');

  function showError(message) { $('#errorAlert').text(message).removeClass('d-none'); }
  function clearError() { $('#errorAlert').text('').addClass('d-none'); }
  function clearResult() { $('#resultContent').addClass('d-none'); $('#emptyResult').removeClass('d-none'); }

  function selectFile(file) {
    clearError();
    if (!file) return;
    if (!allowed.includes(file.type)) { showError('Choose a PNG, JPEG, GIF, WEBP, or BMP image.'); return; }
    if (file.size > maxBytes) { showError('The image must be 5 MB or smaller.'); return; }
    selectedFile = file;
    $('#fileName').text(file.name);
    $('#selectedFile').removeClass('d-none');
    $('#solveBtn').prop('disabled', false);
    clearResult();
    const reader = new FileReader();
    reader.onload = function (event) {
      $('#imagePreview').attr('src', event.target.result);
      $('#previewWrap').removeClass('d-none');
      $('#uploadHint').addClass('d-none');
    };
    reader.readAsDataURL(file);
  }

  function reset() {
    selectedFile = null;
    $input.val('');
    $('#previewWrap, #selectedFile').addClass('d-none');
    $('#imagePreview').removeAttr('src');
    $('#uploadHint').removeClass('d-none');
    $('#solveBtn').prop('disabled', true);
    clearError();
    clearResult();
  }

  $('#dropzone').on('click', function () { $input.trigger('click'); });
  $('#dropzone').on('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); $input.trigger('click'); } });
  $input.on('change', function () { selectFile(this.files[0]); });
  $('#dropzone').on('dragover dragenter', function (e) { e.preventDefault(); e.stopPropagation(); $(this).addClass('dragging'); });
  $('#dropzone').on('dragleave dragend', function (e) { e.preventDefault(); e.stopPropagation(); $(this).removeClass('dragging'); });
  async function loadSample(name) {
    if (!name) return;
    try {
      const response = await fetch('/samples/image/' + encodeURIComponent(name));
      if (!response.ok) throw new Error('Sample image not found.');
      const blob = await response.blob();
      selectFile(new File([blob], name, {type: blob.type || 'image/png'}));
    } catch (err) { showError(err.message || 'Unable to load sample.'); }
  }

  $('#dropzone').on('drop', function (e) {
    e.preventDefault(); e.stopPropagation(); $(this).removeClass('dragging');
    const transfer = e.originalEvent.dataTransfer;
    if (transfer.files.length) { selectFile(transfer.files[0]); return; }
    // Dragging a sample image from another browser tab supplies an image URL.
    const url = transfer.getData('text/uri-list') || transfer.getData('text/plain');
    try {
      const parsed = new URL(url, window.location.href);
      const prefix = '/samples/image/';
      if (parsed.origin === window.location.origin && parsed.pathname.startsWith(prefix)) {
        loadSample(decodeURIComponent(parsed.pathname.slice(prefix.length)));
        return;
      }
    } catch (_) { /* Not a URL */ }
    showError('Drop an image file or a sample from the Samples page.');
  });
  const querySample = new URLSearchParams(window.location.search).get('sample');
  if (querySample) loadSample(querySample);
  $('#removeFile').on('click', function (e) { e.stopPropagation(); reset(); });
  $('#resetBtn').on('click', reset);

  $('#solveBtn').on('click', function () {
    if (!selectedFile) return;
    clearError();
    const form = new FormData();
    form.append('image', selectedFile);
    form.append('captcha_type', $('#captchaType').val());
    $('#solveBtn').prop('disabled', true);
    $('#solveBtnText').addClass('d-none');
    $('#solveSpinner').removeClass('d-none');
    $.ajax({
      url: '/api/solve', method: 'POST', data: form, processData: false, contentType: false,
      headers: {'Authorization': 'Bearer ' + $('#apiToken').val().trim()},
      success: function (data) {
        $('#resultText').text(data.result || '(No text detected)');
        $('#elapsedText').text(data.processing_time_ms.toLocaleString() + ' ms');
        $('#emptyResult').addClass('d-none');
        $('#resultContent').removeClass('d-none');
      },
      error: function (xhr) { showError(xhr.responseJSON?.error || 'Unable to solve the image.'); },
      complete: function () {
        $('#solveBtn').prop('disabled', !selectedFile);
        $('#solveBtnText').removeClass('d-none');
        $('#solveSpinner').addClass('d-none');
      }
    });
  });

  $('#copyBtn').on('click', function () {
    const text = $('#resultText').text();
    if (!navigator.clipboard) { showError('Clipboard not available in this browser context.'); return; }
    navigator.clipboard.writeText(text).then(() => {
      const $icon = $(this).find('i'); $icon.removeClass('bi-copy').addClass('bi-check2');
      setTimeout(() => $icon.removeClass('bi-check2').addClass('bi-copy'), 1500);
    }).catch(() => showError('Unable to copy text.'));
  });

  $.getJSON('/api/health').done(function (data) {
    $('#modelStatus').addClass(data.ready ? 'ready' : 'offline');
    $('#statusText').text(data.message);
  }).fail(function () {
    $('#modelStatus').addClass('offline');
    $('#statusText').text('Model unavailable');
  });
});
