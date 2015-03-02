
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

});
