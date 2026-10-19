/* ============================================================
   IHM - lógica do painel 16:9 (apenas exibição)
   Renderiza KPIs, gráfico histórico e estatísticas, e faz
   polling do endpoint JSON para atualizar sem flicker.
   ============================================================ */

var IHM_COLORS = ['#059bff', '#ff4069', '#ff9020', '#22cfcf', '#a06bff', '#2fd07a'];

/* ============================================================
   Alarme sonoro quando a espessura está fora dos limites.
   Usa a Web Audio API (sem arquivos externos) e respeita o
   cooldown configurável em Configurações e Debug
   (payload.alarm.cooldown_seconds, padrão 180 s).
   ============================================================ */

var alarmCtx = null;
var lastAlarmAt = 0;

function getAlarmCtx() {
    if (!alarmCtx) {
        var Ctx = window.AudioContext || window.webkitAudioContext;
        if (!Ctx) return null;
        try {
            alarmCtx = new Ctx();
        } catch (e) {
            alarmCtx = null;
        }
    }
    return alarmCtx;
}

function unlockAlarmAudio() {
    // Navegadores bloqueiam áudio até o primeiro gesto do usuário. Depois de
    // liberado, o próximo polling dispara o alarme se houver não conformidade.
    var ctx = getAlarmCtx();
    if (ctx && ctx.state === 'suspended') {
        ctx.resume().catch(function () {});
    }
}

function emitAlarmBeeps(ctx) {
    var t0 = ctx.currentTime;
    for (var i = 0; i < 3; i++) {
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        var start = t0 + i * 0.35;
        var duration = 0.22;
        osc.type = 'square';
        osc.frequency.value = 880;
        gain.gain.setValueAtTime(0, start);
        gain.gain.linearRampToValueAtTime(0.2, start + 0.01);
        gain.gain.setValueAtTime(0.2, start + duration - 0.01);
        gain.gain.linearRampToValueAtTime(0, start + duration);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(start);
        osc.stop(start + duration);
    }
}

function playAlarmSound() {
    var ctx = getAlarmCtx();
    if (!ctx || ctx.state === 'closed') return false;
    if (ctx.state !== 'running') {
        if (ctx.state === 'suspended') {
            ctx.resume().catch(function () {});
        }
        return false;
    }
    emitAlarmBeeps(ctx);
    return true;
}

function maybeSoundAlarm(payload) {
    if (!payload.out_of_limits) return;
    var cooldownSeconds = (payload.alarm && payload.alarm.cooldown_seconds) || 180;
    var cooldownMs = cooldownSeconds * 1000;
    var now = Date.now();
    if (lastAlarmAt && (now - lastAlarmAt) < cooldownMs) return;
    if (playAlarmSound()) {
        lastAlarmAt = now;
    }
}

function fmt(value, decimals) {
    if (value === null || value === undefined || isNaN(value)) {
        return '—';
    }
    return Number(value).toFixed(decimals === undefined ? 2 : decimals);
}

function windowLabel(hours) {
    if (hours === 1) {
        return 'última hora';
    }
    return 'últimas ' + hours + ' horas';
}

function renderKpis(payload) {
    var row = document.getElementById('kpi-row');
    if (!row) return;
    var html = '';
    payload.positions.forEach(function (p) {
        var cls = 'kpi-card';
        if (p.out_of_limits) cls += ' out';
        else if (p.stale) cls += ' stale';
        html += '' +
            '<div class="' + cls + '">' +
                '<div class="kpi-name">' + (p.name || 'Ponto') + '</div>' +
                '<div class="kpi-value">' +
                    '<span class="num">' + fmt(p.current) + '</span>' +
                    '<span class="unit">mm</span>' +
                '</div>' +
                '<div class="kpi-meta">' +
                    '<span>mín <b>' + fmt(p.min) + '</b></span>' +
                    '<span>méd <b>' + fmt(p.avg) + '</b></span>' +
                    '<span>máx <b>' + fmt(p.max) + '</b></span>' +
                    '<span>n <b>' + (p.count || 0) + '</b></span>' +
                '</div>' +
                '<div class="kpi-foot">' +
                    '<span>Leitura ' + (p.current_time || '—') + '</span>' +
                    '<span>Calib ' + (p.last_calibration || '—') + '</span>' +
                '</div>' +
            '</div>';
    });
    row.innerHTML = html;
}

function renderStats(payload) {
    var row = document.getElementById('stats-row');
    if (!row) return;
    var f = payload.footer || {};
    var tiles = [
        { label: 'Média 15 min', value: fmt(f.avg15) },
        { label: 'Média 30 min', value: fmt(f.avg30) },
        { label: 'Média 60 min', value: fmt(f.avg60) },
        { label: 'Média ' + payload.hours + ' h', value: fmt(f.avg_window) },
        { label: 'Desvio padrão', value: fmt(f.std) },
        { label: 'Espessura mín.', value: fmt(f.min) },
        { label: 'Espessura máx.', value: fmt(f.max) },
        { label: '% Inconformidade (1 h)', value: fmt(f.perc) + '%', bad: f.perc > 0 },
        { label: 'Medições / min', value: fmt(f.freq) }
    ];
    var html = '';
    tiles.forEach(function (t) {
        var cls = 'stat-value' + (t.bad ? ' bad' : '');
        html += '' +
            '<div class="stat-tile">' +
                '<div class="stat-label">' + t.label + '</div>' +
                '<div class="' + cls + '">' + t.value + '</div>' +
            '</div>';
    });
    row.innerHTML = html;
}

function renderHeader(payload) {
    var name = document.getElementById('machine-name');
    if (name) name.textContent = payload.machine_name;

    var updated = document.getElementById('updated-at');
    if (updated) updated.textContent = 'Dados ' + (payload.updated_at || '—');

    var win = document.getElementById('chart-window');
    if (win) win.textContent = windowLabel(payload.hours);

    var pill = document.getElementById('status-pill');
    if (!pill) return;
    pill.className = 'status-pill';
    if (payload.out_of_limits) {
        pill.textContent = 'ALERTA';
        pill.classList.add('bad');
    } else if (payload.stale) {
        pill.textContent = 'SEM DADOS';
        pill.classList.add('warn');
    } else {
        pill.textContent = 'AO VIVO';
    }
}

function buildDatasets(payload) {
    var datasets = [];
    payload.chart.series.forEach(function (s, i) {
        var color = IHM_COLORS[i % IHM_COLORS.length];
        datasets.push({
            label: s.name,
            borderColor: color,
            backgroundColor: color,
            data: s.values,
            spanGaps: false,
            fill: false,
            cubicInterpolationMode: 'monotone',
            tension: 0.1,
            pointRadius: 0,
            borderWidth: 2
        });
    });

    var len = payload.chart.labels.length;
    var dash = { borderDash: [6, 4], borderWidth: 2, fill: false, pointRadius: 0 };
    datasets.push({
        label: 'Limite Superior',
        data: Array(len).fill(payload.limits.upper),
        borderColor: '#ff4069',
        borderDash: dash.borderDash,
        borderWidth: dash.borderWidth,
        fill: dash.fill,
        pointRadius: dash.pointRadius
    });
    datasets.push({
        label: 'Limite Inferior',
        data: Array(len).fill(payload.limits.lower),
        borderColor: '#ff4069',
        borderDash: dash.borderDash,
        borderWidth: dash.borderWidth,
        fill: dash.fill,
        pointRadius: dash.pointRadius
    });
    return datasets;
}

var ihmChart = null;

function createIhmChart(payload) {
    var canvas = document.getElementById('ihm-chart');
    if (!canvas || typeof Chart === 'undefined') return;
    var ctx = canvas.getContext('2d');

    ihmChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: payload.chart.labels,
            datasets: buildDatasets(payload)
        },
        options: {
            animation: false,
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#5c6b84', boxWidth: 18, font: { size: 12 } }
                }
            },
            scales: {
                y: {
                    min: payload.graph_limits.lower,
                    max: payload.graph_limits.upper,
                    ticks: { color: '#5c6b84' },
                    grid: { color: 'rgba(91,107,133,0.18)' }
                },
                x: {
                    ticks: {
                        color: '#5c6b84',
                        autoSkip: true,
                        maxTicksLimit: 12,
                        maxRotation: 0,
                        minRotation: 0
                    },
                    grid: { color: 'rgba(91,107,133,0.10)' }
                }
            }
        }
    });
}

function updateIhmChart(payload) {
    if (!ihmChart) return;
    ihmChart.data.labels = payload.chart.labels;
    ihmChart.data.datasets = buildDatasets(payload);
    ihmChart.options.scales.y.min = payload.graph_limits.lower;
    ihmChart.options.scales.y.max = payload.graph_limits.upper;
    ihmChart.update('none');
}

function render(payload) {
    renderHeader(payload);
    renderKpis(payload);
    renderStats(payload);
}

function refresh() {
    var meta = window.__IHM_META__ || {};
    var url = meta.dataUrl + '?hours=' + (meta.hours || 1);
    fetch(url)
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data && data.chart) {
                window.__IHM__ = data;
                render(data);
                updateIhmChart(data);
                maybeSoundAlarm(data);
            }
        })
        .catch(function () {
            var pill = document.getElementById('status-pill');
            if (pill) {
                pill.textContent = 'OFFLINE';
                pill.className = 'status-pill bad';
            }
        });
}

function tickClock() {
    var el = document.getElementById('clock');
    if (!el) return;
    var now = new Date();
    var hh = String(now.getHours()).padStart(2, '0');
    var mm = String(now.getMinutes()).padStart(2, '0');
    var ss = String(now.getSeconds()).padStart(2, '0');
    el.textContent = hh + ':' + mm + ':' + ss;
}

window.addEventListener('load', function () {
    var payload = window.__IHM__;
    if (!payload) return;
    ['pointerdown', 'keydown', 'touchstart'].forEach(function (evt) {
        window.addEventListener(evt, unlockAlarmAudio);
    });
    render(payload);
    createIhmChart(payload);
    maybeSoundAlarm(payload);
    tickClock();
    setInterval(tickClock, 1000);
    setInterval(refresh, 10000);
});
