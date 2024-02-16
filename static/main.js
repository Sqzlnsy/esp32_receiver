// main.js
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

document.getElementById('addPlotButton').addEventListener('click', function() {
    var plotsList = document.getElementById('plotsList');
    plotsList.style.display = 'block'; // Show the list
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
                // Optionally, refresh part of your page or show a notification
            } else {
                console.error('Failed to update active series');
            }
        }).catch(error => console.error('Error:', error));
    }
});

function initializePlot(containerId, series) {
    // Replace this with your actual plot initialization code
    // For example, if using CanvasJS:
    var chart = new CanvasJS.Chart(containerId, {
        title: {
            text: `Plot for ${series}`
        },
        data: [
            // Your data here
        ]
    });
    chart.render();
}

// Canvas.js chart setup
window.onload = function () {
    const plotsContainer = document.querySelector('.plots-container');
    const activeSeries = JSON.parse(plotsContainer.getAttribute('data-active-series'));

    activeSeries.forEach(function(series) {
        const containerId = `chartContainer_${series}`;
        const container = document.createElement('div');
        container.id = containerId;
        container.style.height = '300px';
        container.style.width = '100%';
        plotsContainer.appendChild(container);

        // Initialize the plot for this series
        initializePlot(containerId, series);
    });
};
