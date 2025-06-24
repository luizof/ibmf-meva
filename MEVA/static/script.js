function createChart(elementId, labels, upperLimit, lowerLimit, graphData) {
    var ctx = document.getElementById(elementId).getContext('2d');
    var colors = ['#059bff', '#ff4069', '#ff9020', '#22cfcf'];
    
    var datasets = [];
    var dataMin = Infinity;
    var dataMax = -Infinity;
    for (var i = 0; i < graphData.length; i++) {
        var position_data = graphData[i];
        var color = colors[i % colors.length]; // Seleciona a cor com base no índice
        var values = position_data[1];
        // Atualiza limites encontrados nos dados
        for (var j = 0; j < values.length; j++) {
            var v = values[j];
            if (v !== null && !isNaN(v)) {
                dataMin = Math.min(dataMin, v);
                dataMax = Math.max(dataMax, v);
            }
        }
        datasets.push({
            label: position_data[0],
            borderColor: color, // Use a cor selecionada
            data: values,
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

    // Determina os limites do eixo Y usando os dados quando disponíveis
    if (dataMin === Infinity) {
        dataMin = lowerLimit;
    }
    if (dataMax === -Infinity) {
        dataMax = upperLimit;
    }

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
                    min: Math.min(lowerLimit - 0.5, dataMin - 0.1),
                    max: Math.max(upperLimit + 0.5, dataMax + 0.1)
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

function createMiniChart(elementId, labels, upperLimit, lowerLimit, values) {
    var canvas = document.getElementById(elementId);
    if (window.innerWidth <= 768) {
        canvas.height = 300;
    }
    var ctx = canvas.getContext('2d');

    var dataMin = Infinity;
    var dataMax = -Infinity;
    for (var i = 0; i < values.length; i++) {
        var v = values[i];
        if (v !== null && !isNaN(v)) {
            dataMin = Math.min(dataMin, v);
            dataMax = Math.max(dataMax, v);
        }
    }

    if (dataMin === Infinity) {
        dataMin = lowerLimit;
    }
    if (dataMax === -Infinity) {
        dataMax = upperLimit;
    }

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
                    min: Math.min(lowerLimit - 0.5, dataMin - 0.1),
                    max: Math.max(upperLimit + 0.5, dataMax + 0.1)
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
