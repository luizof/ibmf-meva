function createChart(elementId, labels, upperLimit, lowerLimit, graphData) {
    var ctx = document.getElementById(elementId).getContext('2d');
    var colors = ['#059bff', '#ff4069', '#ff9020', '#22cfcf'];
    
    var datasets = [];
    for (var i = 0; i < graphData.length; i++) {
        var position_data = graphData[i];
        var color = colors[i % colors.length]; // Seleciona a cor com base no índice
        datasets.push({
            label: position_data[0],
            borderColor: color, // Use a cor selecionada
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
                    min: (lowerLimit - 0.5),
                    max: (upperLimit + 0.5)
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
    var ctx = document.getElementById(elementId).getContext('2d');
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
                    min: (lowerLimit - 0.5),
                    max: (upperLimit + 0.5)
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
