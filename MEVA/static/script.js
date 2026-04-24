function createChart(elementId, labels, upperLimit, lowerLimit, graphData, graphMin, graphMax) {
    var ctx = document.getElementById(elementId).getContext('2d');
    var colors = ['#059bff', '#ff4069', '#ff9020', '#22cfcf'];
    
    var datasets = [];
    for (var i = 0; i < graphData.length; i++) {
        var position_data = graphData[i];
        var color = colors[i % colors.length]; // Seleciona a cor com base no índice
        datasets.push({
            label: position_data[0],
            borderColor: color,
            data: position_data[1],
            spanGaps: true,
            fill: false,
            cubicInterpolationMode: 'monotone',
            tension: 0.1,
            pointRadius: 0
        });
    }

    datasets.push({
        label: 'Limite Superior',
        data: Array(labels.length).fill(upperLimit),
        borderColor: 'red',
        borderWidth: 1,
        fill: false,
        pointRadius: 0
    });

    datasets.push({
        label: 'Limite Inferior',
        data: Array(labels.length).fill(lowerLimit),
        borderColor: 'red',
        borderWidth: 1,
        fill: false,
        pointRadius: 0
    });

    var chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            animation: false,
            scales: {
                y: {
                    // Y-axis is fixed to the global graph scale.
                    // Values outside [graphMin, graphMax] are already clamped server-side.
                    min: graphMin,
                    max: graphMax
                },
                x: {
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 10,
                        maxRotation: 0,
                        minRotation: 0
                    }
                }
            }
        }
    });
}

function createMiniChart(elementId, labels, upperLimit, lowerLimit, values, graphMin, graphMax) {
    var canvas = document.getElementById(elementId);
    if (window.innerWidth <= 768) {
        canvas.height = 300;
    }
    var ctx = canvas.getContext('2d');

    var chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Espessura',
                    borderColor: '#059bff',
                    data: values,
                    spanGaps: true,
                    fill: false,
                    cubicInterpolationMode: 'monotone',
                    tension: 0.1,
                    pointRadius: 0
                },
                {
                    label: 'Limite Superior',
                    data: Array(labels.length).fill(upperLimit),
                    borderColor: 'red',
                    borderWidth: 1,
                    fill: false,
                    pointRadius: 0
                },
                {
                    label: 'Limite Inferior',
                    data: Array(labels.length).fill(lowerLimit),
                    borderColor: 'red',
                    borderWidth: 1,
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: {
            animation: false,
            scales: {
                y: {
                    // Y-axis is fixed to the global graph scale.
                    // Values outside [graphMin, graphMax] are already clamped server-side.
                    min: graphMin,
                    max: graphMax
                },
                x: {
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 10,
                        maxRotation: 0,
                        minRotation: 0
                    }
                }
            }
        }
    });
}

function formatLocalDateTime(dt) {
    var year = dt.getFullYear();
    var month = String(dt.getMonth() + 1).padStart(2, '0');
    var day = String(dt.getDate()).padStart(2, '0');
    var hour = String(dt.getHours()).padStart(2, '0');
    var minute = String(dt.getMinutes()).padStart(2, '0');
    return year + '-' + month + '-' + day + 'T' + hour + ':' + minute;
}

function moveHistory(minutes) {
    var input = document.getElementById('datetime');
    var current = input.value;
    var dt = current ? new Date(current) : new Date();
    dt.setMinutes(dt.getMinutes() + minutes);
    input.value = formatLocalDateTime(dt);
    document.getElementById('history-form').submit();
}

function setRange(hours) {
    var dt = new Date();
    dt.setHours(dt.getHours() - hours);
    document.getElementById('datetime').value = formatLocalDateTime(dt);
    document.getElementById('hours').value = hours;
    document.getElementById('history-form').submit();
}
