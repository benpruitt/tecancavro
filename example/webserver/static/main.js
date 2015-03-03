
$(document).ready(function() {

+$( "#extract_btn" ).click(function( event ) {
    var volume = $( "#extract_volume").val();
    var port = $("#port_number").val();
    var serport = $( "#serial_port").val() || '';
    if ( volume > 0 && volume < 1000) {
        $( "#debugfield" ).text( "Valid extract command..." ).show();
        $.get('extract',
              {'volume': volume,
               'port': port,
               'serial_port': serport
                }
            );
    } else {
        $( "#debugfield" ).text( "Not valid extract command!" ).show().fadeOut( 1000 );
    }
    event.preventDefault();
});

$( "#dispense_btn" ).click(function( event ) {

    var volume = $( "#dispense_volume").val();
    var port = $("#port_number").val();
    var serport = $( "#serial_port").val() || '';
    if ( volume > 0 && volume < 1000) {
        $( "#debugfield" ).text( "Validated dispense command..." ).show();
        $.get('dispense',
              {'volume': volume,
               'port': port,
               'serial_port': serport
                }
            );
    } else {
        $( "#debugfield" ).text( "Not valid dispense command!" ).show().fadeOut( 1000 );
    }
    event.preventDefault();
});

$( "#submitProtocol" ).click(function( event ) {

    var oTable = document.getElementById('protocolTable');

    //gets rows of table
    var rowLength = oTable.rows.length;

    var volume;
    var inport;
    var outport;
    var flowRate;
    var time;
    var serport = $( "#serial_port").val() || '';

    //loops through rows    
    for (i = 1; i < rowLength; i++){

       //gets cells of current row
       var oCells = oTable.rows.item(i).cells;

       //gets amount of cells of current row
       var cellLength = oCells.length;

       
       /* var cellVal = oCells.item(j).innerHTML; */
       str = oCells.item(3).innerHTML;
       var numberPattern = /\d+/g;
       var idnum = str.match( numberPattern )[1]
       var idstr = "from" + idnum;
       var inportId = document.getElementById(idstr);

       inport = inportId.options[inportId.selectedIndex].value;
       var idstr = "to" + idnum;
       var inportId = document.getElementById(idstr);
       outport = inportId.options[inportId.selectedIndex].value;
    
        var idstr = "vol" + idnum;
        var volId = document.getElementById(idstr);
        volume = volId.value

        var idstr = "rate" + idnum;
        var rateId = document.getElementById(idstr);
        flowRate = rateId.value

        var idstr = "time" + idnum;
        var timeId = document.getElementById(idstr);
        time = timeId.value
        
        $.get('extract',
              {'volume': volume,
               'port': inport,
               'serial_port': serport
                }
            );
        $.get('dispense',
              {'volume': volume,
               'port': outport,
               'serial_port': serport
                }
            );

    }
    //send command to execute
    $.get('execute',
              {'serial_port': serport
                }
            );

    event.preventDefault();
});



protocolItems = 1;

$( "#newrows" ).click(function( event ) {
    protocolItems = protocolItems + 1;
    //$("#addspot").append("hi").show();
    var table = document.getElementById("protocolTable");
    var row = table.insertRow(protocolItems);
    var cell1 = row.insertCell(0);
    var cell2 = row.insertCell(1);
    var cell3 = row.insertCell(2);
    var cell4 = row.insertCell(3);
    var cell5 = row.insertCell(4);
    var cell6 = row.insertCell(5);

    cell1.innerHTML = "<label>" + protocolItems + ")</label>";
    cell2.innerHTML = "<div class = 'col-lg-12'><select id = 'from" + protocolItems + "' class='form-control'><option value='1'>1</option><option value='2'>2</option><option value='3'>3</option><option value='4'>4</option><option value='5'>5</option><option value='6'>6</option><option value='7'>7</option><option value='8'>8</option><option value='9'>9</option></select></div>";
    cell3.innerHTML = "<div class = 'col-lg-12'><select id = 'to" + protocolItems + "' class='form-control'><option value='1'>1</option><option value='2'>2</option><option value='3'>3</option><option value='4'>4</option><option value='5'>5</option><option value='6'>6</option><option value='7'>7</option><option value='8'>8</option><option value='9' selected>9</option></select></div>";
    cell4.innerHTML = "<div class = 'col-lg-8'><div class='form-group'><input id = 'time" + protocolItems + "' class='form-control' placeholder='Seconds'></div></div>";
    cell5.innerHTML = "<div class = 'col-lg-8'><div class='form-group'><input id = 'rate" + protocolItems + "' class='form-control' placeholder='ul/sec'></div></div>";
    cell6.innerHTML = "<div class = 'col-lg-8'><div class='form-group'><input id = 'vol" + protocolItems + "' class='form-control' placeholder='ul'></div></div>"


    


    event.preventDefault();
});

});
