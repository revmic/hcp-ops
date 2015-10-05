$(function () {
    $.getJSON('http://hcp-ops.nrg.mir/stats/geolocation', function (data) {

        var countryData = data["results"];
        var mapData = Highcharts.geojson(Highcharts.maps['custom/world']);

        var chart = new Highcharts.Map({
            chart: {
                renderTo: 'data-dist',
                border: 0
            },
            title: {
                text: ''
            },

            subtitle : {
                text : ''
            },

            legend: {
                enabled: false
            },

            mapNavigation: {
                enabled: true,
                buttonOptions: {
                    verticalAlign: 'bottom'
                }
            },

            series : [{
                name: 'Countries',
                mapData: mapData,
                color: '#E0E0E0',
                enableMouseTracking: false
            }, {
                type: 'mapbubble',
                mapData: mapData,
                name: 'Connectome Data',
                joinBy: ['iso-a2', 'code'],
                data: countryData,
                //color: '#00176B',
                //  #217AA0
                minSize: 4,
                maxSize: '12%',
                tooltip: {
                    pointFormat: '{point.country}: <br>{point.downloads} GB Downloaded <br>{point.orders} GB Shipped'
                }
            }]
        });
    });
});

// chart.series[0].setData(data,true);

//var aspera_chart;

$(function () {
    $.getJSON('http://hcp-ops.nrg.mir/stats/downloads', function (data) {

        // Initially load for 'All' projects
        for (var i in data["results"]) {
            if (data["results"][i]["project"] == 'All') {
                var all_data = data["results"][i];
                break;
            }
        }

        var months = all_data["months"];
        var terabytes = all_data["terabytes"];
        var users = all_data["users"];
        var files = all_data["files_thousands"];

        //aspera_chart =
        $('#aspera-month').highcharts({
            title: {
                text: 'Downloads per Month',
                x: -20 //center
            },
            subtitle: {
                text: '',
                x: -20
            },
            xAxis: {
                categories: months
            },
            yAxis: {
                title: {
                    text: ''
                },
                plotLines: [{
                    value: 0,
                    width: 1,
                    color: '#808080'
                }]
            },
            tooltip: {
                valueSuffix: ''
            },
            legend: {
                layout: 'vertical',
                align: 'right',
                verticalAlign: 'middle',
                borderWidth: 0
            },
            series: [{
                name: 'Terabytes',
                data: terabytes
                //color: "#D62839"
            }, {
                name: 'Distinct Users',
                data: users
                //color: "#247BA0"
            }, {
                name: 'Files (thousands)',
                data: files,
                color: "#031A6B"
            }]
        });
    });

    //$('#aspera-month a').click(function() {
    //    var chart = $('#aspera-month').highcharts();
    //    var proj = $(this).text();
    //    alert(proj);
    //
    //    chart.series[0].setData([129.2, 144.0, 176.0, 135.6, 148.5, 216.4, 194.1, 95.6, 54.4, 29.9, 71.5, 106.4]);
    //});
});

function updateAsperaChart(project) {
    //alert($('.nav-pills .active').text());
    var chart = $('#aspera-month').highcharts();

    $.getJSON('http://hcp-ops.nrg.mir/stats/downloads', function (data) {

        for (var i in data["results"]) {
            if (data["results"][i]["project"] == project) {
                var projData = data["results"][i];
                break;
            }
        }

        var months = projData["months"];
        var terabytes = projData["terabytes"];
        var users = projData["users"];
        var files = projData["files_thousands"];

        chart.series[0].setData(terabytes, true);
        chart.series[1].setData(users, true);
        chart.series[2].setData(files, true);
    });
}


//$(document).ready(function() {
//    // tab
//    $('#asperaTabs a:first').tab('show');
//
//    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
//        //show selected tab / active
//         console.log($(e.target).attr('id'));
//    });
//});
