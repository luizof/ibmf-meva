/* ============================================================
   Status de Sensores - atualização contínua (polling)
   Atualiza os badges de conexão sem recarregar a página.
   ============================================================ */

function applySensorStatus(payload) {
    (payload.sensors || []).forEach(function (s) {
        var el = document.getElementById('sensor-' + s.id);
        if (!el) return;
        el.className = s.status;
        el.textContent = s.status === 'connected' ? 'Conectado' : 'Desconectado';
    });

    var lu = document.getElementById('last-update');
    if (lu) lu.textContent = payload.updated_at || '--:--:--';
}

var _statusBusy = false;

function pollStatus() {
    if (_statusBusy) return;
    _statusBusy = true;
    var meta = window.__STATUS_META__ || {};
    fetch(meta.dataUrl)
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data && data.sensors) applySensorStatus(data);
        })
        .catch(function () {
            // Falha de rede: mantém o último estado conhecido
        })
        .finally(function () {
            _statusBusy = false;
        });
}

window.addEventListener('load', function () {
    var meta = window.__STATUS_META__ || {};
    pollStatus();
    setInterval(pollStatus, meta.pollMs || 5000);
});
