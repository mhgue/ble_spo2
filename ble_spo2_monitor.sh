#!/bin/bash

SPO2_LOW=89
SPO2_HIGH=99

# Check for MAC
if [ -z "$O2_BLE_MAC" ]; then
    echo "Do export your SpO2 sensor MAC using"
    echo "export O2_BLE_MAC=DA:1C:F9:12:34:56"
    exit
fi

# Check for language to use
LANGUAGE=$(locale | grep LANGUAGE | cut -d= -f2 | cut -d_ -f1)
SPEAK="espeak -v $LANGUAGE"

# Texts for different languages
case $LANGUAGE in
"en")
    export LANG_START=Start_monitoring
    export LANG_HIGH=high_oxygen
    export LANG_LOW=low_oxygen
    export LANG_INACT=sensor_idle
    export LANG_OFF=sensor_off
    ;;
"de")
    export LANG_START=Überwachung_starten
    export LANG_HIGH=viel_Sauerstoff
    export LANG_LOW=wenig_Sauerstoff
    export LANG_INACT=Sensor_inaktiv
    export LANG_OFF=Sensor_aus
    ;;
"es")
    export LANG_START=comenzar_a_monitorear
    export LANG_HIGH=mucho_oxigeno
    export LANG_LOW=poco_oxigeno
    export LANG_INACT=sensor_inactivo
    export LANG_OFF=sensor_apagado
    ;;
*)
    echo "LANGUAGE $LANGUAGE not supported"
    exit
    ;;
esac

# Let monitoring run in infinite loop
# to restart imediately if python throws an exception.
while true; do
    $SPEAK $LANG_START
    ./ble_spo2.py -i \
        --o2_max $SPO2_HIGH --o2_high_action "$SPEAK $LANG_HIGH" \
        --o2_min $SPO2_LOW --o2_low_action "$SPEAK $LANG_LOW" \
        --sensor_idle_action "$SPEAK $LANG_INACT" \
        --sensor_off_action "$SPEAK $LANG_OFF" \
        $O2_BLE_MAC
done

#EOF
