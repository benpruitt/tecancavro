
$(document).ready(function() {

+$( "#extract_btn" ).click(function( event ) {
    var volume = $( "#extract_volume").val();
    var port = $("#port_number").val();
    var serport = $( "#serial_port").val() || '';
    var rate = $("#rate_box").val();
    
    if ( volume > 0 && volume <= 5000) {
        $( "#debugfield" ).text( "Valid extract command..." ).show();
        $.get('extract',
              {'volume': volume,
               'port': port,
               'serial_port': serport,
               'exec': 1,
               'rate': rate
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
    var rate = $("#rate_box").val();
    
    if ( volume > 0 && volume <= 5000) {
        $( "#debugfield" ).text( "Validated dispense command..." ).show();
        $.get('dispense',
              {'volume': volume,
               'port': port,
               'serial_port': serport,
               'exec': 1,
               'rate': rate
                }
            );
        
    } else {
        $( "#debugfield" ).text( "Not valid dispense command!" ).show().fadeOut( 1000 );
    }

    event.preventDefault();
});
$( "#stop_exec" ).click(function( event ) {

    var serport = $( "#serial_port").val() || '';
        $.get('halt',
              {'serial_port': serport
                }
            );
    
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
    $.get('clear_chain',
              {'serial_port': serport
                }
            );


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
               'serial_port': serport,
               'exec': 0,
               'rate': flowRate
                }
            );
        $.get('dispense',
              {'volume': volume,
               'port': outport,
               'serial_port': serport,
               'exec': 0,
               'rate': flowRate
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

$( "#submitProtocolAdv" ).click(function( event ) {

  var serport = $( "#serial_port").val() || '';
  var oTable = document.getElementById('protocolTable');
  var rowLength = oTable.rows.length;
  var fromports = [];
  var toports = [];
  var datetimes = [];
  var flowrates = [];
  var volumes = [];
  var finals = [];

  for (i = 1; i < rowLength; i++){
      var oCells = oTable.rows.item(i).cells;

       //gets amount of cells of current row
      var cellLength = oCells.length;

      str = oCells.item(3).innerHTML;

      var numberPattern = /\d+/g;
      var idnum = str.match( numberPattern )[1]

      var idstr = "from" + idnum;
      var inportId = document.getElementById(idstr);
      inport = inportId.options[inportId.selectedIndex].value;
      fromports[i-1] = inport;
      var idstr = "to" + idnum;
      var inportId = document.getElementById(idstr);
       outport = inportId.options[inportId.selectedIndex].value;
       toports[i-1] = outport;
    
        var idstr = "vol" + idnum;
        var volId = document.getElementById(idstr);
        volume = volId.value
        volumes[i-1] = volume

        var idstr = "rate" + idnum;
        var rateId = document.getElementById(idstr);
        flowRate = rateId.value
        flowrates[i-1] = flowRate;

        var idstr = "date" + idnum;
        var dateId = document.getElementById(idstr);
        date = dateId.value
        var idstr = "final" + idnum;
        var finalId = document.getElementById(idstr);
        finals[i-1] = finalId.value

        var idstr = "time" + idnum;
        var timeId = document.getElementById(idstr);
        time = timeId.value
        var datesplit = date.split("/");
        var timesplit = time.split(" ");
        var timedsplit = timesplit[0].split(":")
        var hourI = parseInt(timedsplit[0])
        var min = timedsplit[1]
        var year = datesplit[2]
        var day = datesplit[1]
        var month = datesplit[0]
        if(hourI == 12){
          hourI = 0
        }

        if (timesplit[1] === "PM")
          hourI = hourI + 12
        var hour = hourI.toString()
        if(hourI <10)
          hour = '0' + hour
        if(min.length != 2)
          min = "0" + min
        var datetime = year + '-' + month + "-" + day + " " + hour + ":" + min +":00"
       datetimes[i-1] = datetime

        var s = '2007-01-01 10:00:00'

  }

    $.get('advProtocol',
              {'numitems': rowLength - 1,
               'fromports': JSON.stringify(fromports),
               'toports': JSON.stringify(toports),
               'serial_port': serport,
               'datetimes': JSON.stringify(datetimes),
               'flowrates': JSON.stringify(flowrates),
               'volumes': JSON.stringify(volumes),
               'finals': JSON.stringify(finals)
                }
            );

    event.preventDefault();
});
$( "#saveProtocol" ).click(function( event ) {

  var serport = $( "#serial_port").val() || '';
  var oTable = document.getElementById('protocolTable');
  var rowLength = oTable.rows.length;
  var fromports = [];
  var toports = [];
  var datetimes = [];
  var flowrates = [];
  var volumes = [];

  for (i = 1; i < rowLength; i++){
      var oCells = oTable.rows.item(i).cells;

       //gets amount of cells of current row
      var cellLength = oCells.length;

      str = oCells.item(3).innerHTML;

      var numberPattern = /\d+/g;
      var idnum = str.match( numberPattern )[1]

      var idstr = "from" + idnum;

      var inportId = document.getElementById(idstr);
           
      inport = inportId.options[inportId.selectedIndex].value;
      fromports[i-1] = inport;
      var idstr = "to" + idnum;
      var inportId = document.getElementById(idstr);
       outport = inportId.options[inportId.selectedIndex].value;
       toports[i-1] = outport;
    
        var idstr = "vol" + idnum;
        var volId = document.getElementById(idstr);
        volume = volId.value
        volumes[i-1] = volume

        var idstr = "rate" + idnum;
        var rateId = document.getElementById(idstr);
        flowRate = rateId.value
        flowrates[i-1] = flowRate;

        var idstr = "date" + idnum;
        var dateId = document.getElementById(idstr);
        date = dateId.value

        var idstr = "time" + idnum;
        var timeId = document.getElementById(idstr);
        time = timeId.value
        var datesplit = date.split("/");
        var timesplit = time.split(" ");
        var timedsplit = timesplit[0].split(":")
        var hourI = parseInt(timedsplit[0])
        var min = timedsplit[1]
        var year = datesplit[2]
        var day = datesplit[1]
        var month = datesplit[0]
        if(hourI == 12){
          hourI = 0
        }

        if (timesplit[1] === "PM")
          hourI = hourI + 12
        var hour = hourI.toString()
        if(hourI <10)
          hour = '0' + hour
        if(min.length != 2)
          min = "0" + min
        var datetime = year + '-' + month + "-" + day + " " + hour + ":" + min +":00"
       datetimes[i-1] = datetime

        var s = '2007-01-01 10:00:00'

  }

    $.get('saveProtocol',
              {'numitems': rowLength - 1,
               'fromports': JSON.stringify(fromports),
               'toports': JSON.stringify(toports),
               'serial_port': serport,
               'datetimes': JSON.stringify(datetimes),
               'flowrates': JSON.stringify(flowrates),
               'volumes': JSON.stringify(volumes)
                }
            );

    event.preventDefault();
});



var oTable = document.getElementById('protocolTable');
var rowLength = oTable.rows.length;
protocolItems = rowLength;
for (i = 1; i < rowLength; i++){
  strdate = "#date" + i 
  $(strdate).datepicker();
  strtime = "#time" + i 
  $(strtime).timepicker();
}

$( "#newrows" ).click(function( event ) {
    var oTable = document.getElementById('protocolTable');
    var rowLength = oTable.rows.length;
    protocolItems = rowLength;
    //$("#addspot").append("hi").show();
    var table = document.getElementById("protocolTable");
    var row = table.insertRow(protocolItems);
    var cell1 = row.insertCell(0);
    var cell2 = row.insertCell(1);
    var cell3 = row.insertCell(2);
    var cell4 = row.insertCell(3);
    var cell5 = row.insertCell(4);
    var cell6 = row.insertCell(5);
    var cell7 = row.insertCell(6);
    var cell8 = row.insertCell(7);

    cell1.innerHTML = "<label>" + protocolItems + "</label>";
    cell2.innerHTML = "<div class = 'col-lg-12'><select id = 'from" + protocolItems + "' class='form-control'><option value='1'>1</option><option value='2'>2</option><option value='3'>3</option><option value='4'>4</option><option value='5'>5</option><option value='6'>6</option><option value='7'>7</option><option value='8'>8</option><option value='9'>9</option></select></div>";
    cell3.innerHTML = "<div class = 'col-lg-12'><select id = 'to" + protocolItems + "' class='form-control'><option value='1'>1</option><option value='2'>2</option><option value='3'>3</option><option value='4'>4</option><option value='5'>5</option><option value='6'>6</option><option value='7'>7</option><option value='8'>8</option><option value='9' selected>9</option></select></div>";
    cell4.innerHTML = "<div class = 'col-lg-12'><select id = 'final" + protocolItems + "' class='form-control'><option value='0' selected>0</option><option value='1'>1</option><option value='2'>2</option><option value='3'>3</option><option value='4'>4</option><option value='5'>5</option><option value='6'>6</option><option value='7'>7</option><option value='8'>8</option><option value='9' >9</option></select></div>";

    cell5.innerHTML = "<div  class = 'col-lg-8'><div class='form-group'><p><input type='text' id='date" + protocolItems+"'></p></div>"
    cell6.innerHTML = "<div  class = 'col-lg-8'><div class='form-group'><div class='input-append bootstrap-timepicker'><input id='time" + protocolItems+"' type='text' class='input-small'><span class='add-on'><i class='icon-time'></i></span></div></div></div>"
    cell7.innerHTML = "<div class = 'col-lg-8'><div class='form-group'><input id = 'rate" + protocolItems + "' class='form-control' placeholder='ul/sec'></div></div>";
    cell8.innerHTML = "<div class = 'col-lg-8'><div class='form-group'><input id = 'vol" + protocolItems + "' class='form-control' placeholder='ul'></div></div>"

    strdate = "#date" + protocolItems 
    $(strdate).datepicker();
    strtime = "#time" + protocolItems 
    $(strtime).timepicker();
    


    event.preventDefault();
});

});
