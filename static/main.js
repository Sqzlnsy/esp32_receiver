// main.js
var charts = {}; 

var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);
socket.on('stream', function(data) {
    var canvas = document.getElementById('videoCanvas');
    var context = canvas.getContext('2d');
    var img = new Image();
    img.onload = function() {
        context.drawImage(img, 0, 0, canvas.width, canvas.height);
    };
    img.src = 'data:image/jpeg;base64,' + data.data;
});

socket.on('update_data', function(data) {
    const containerId = 'chartContainer_' + data.plot_id;
    const newDataPoints = data.data;
    // console.log(data);
    updatePlotData(containerId, newDataPoints);
});

document.addEventListener('DOMContentLoaded', function () {
    var toggleButton = document.getElementById('togglePlotsButton');
    var plotsList = document.getElementById('plotsList');

    toggleButton.addEventListener('click', function () {
        if (plotsList.classList.contains('collapse')) {
            plotsList.classList.remove('collapse');
            toggleButton.textContent = 'Hide Plots';
        } else {
            plotsList.classList.add('collapse');
            toggleButton.textContent = 'Add Plots';
        }
    });

    var sidebarToggle = document.getElementById('sidebarToggle');
    var sidebar = document.getElementById('sidebar');

    sidebarToggle.addEventListener('click', function () {
        sidebar.classList.toggle('active');
    });
});

document.getElementById('plotsForm').addEventListener('change', function(e) {
    if (e.target.type === 'checkbox') {
        const formData = new FormData(this); // Create FormData object from the form
        fetch('/update-active-series', {
            method: 'POST',
            body: formData,
            // Include credentials if your Flask app uses sessions or CSRF protection
            credentials: 'same-origin'
        }).then(response => {
            if (response.ok) {
                console.log('Active series updated successfully');
                return response.json();
            } else {
                console.error('Failed to update active series');
                throw new Error('Failed to update active series');
            }
        }).then(data => {
            // Update active series data in plots-container attribute
            update_plot_lists(data.active_series);
        }).catch(error => console.error('Error:', error));
    }
});

function updatePlotData(containerId, newDataPoints) {
    var chart = charts[containerId];
    if (chart) {
        dps = chart.options.data[0].dataPoints;
        dps.push(...newDataPoints);
        if (dps.length > 100) {
            dps.shift();
        }
        chart.render();
    } else {
        console.log(containerId + " plot does not exist");
    }
}

function initializePlot(containerId, series, dataPoints) {
    var chart = new CanvasJS.Chart(containerId, {
        title: {
            text: `Plot for ${series}`
        },
        data: [{
            type: "line",
            dataPoints: dataPoints
        }]
    });
    chart.render();
    charts[containerId] = chart;
}

function update_plot_lists(active_series){
    const plotsContainer = document.querySelector('.plots-container');
    plotsContainer.setAttribute('data-active-series', JSON.stringify(active_series));
    // Remove existing plots
    const existingPlots = document.querySelectorAll('.plot');
    existingPlots.forEach(plot => plot.remove());
    
    active_series.forEach(series => {
        const newPlot = document.createElement('div');
        newPlot.className = 'plot';
        newPlot.id = 'chartContainer_' + series;
        newPlot.style = 'height: 300px; width: 100%;';
        plotsContainer.appendChild(newPlot);
        initializePlot(newPlot.id, series, []);
    });
    
    console.log('Active series updated successfully');
}
// Canvas.js chart setup
window.onload = function () {
    const plotsContainer = document.querySelector('.plots-container');
    const activeSeries = JSON.parse(plotsContainer.getAttribute('data-active-series'));
    update_plot_lists(activeSeries);
};
