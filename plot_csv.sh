#!/bin/bash

CSV="$1"

gnuplot -persist <<-EOFMarker
set xdata time
set timefmt "%s"
set format x "%H:%M"
set xtics 10
set datafile separator ';'
plot "$CSV" using 2:7 title 'Motion' with linespoints, \
     "$CSV" using 2:4 title 'Pulse' with linespoints, \
     "$CSV" using 2:3 title 'SpO2' with linespoints
EOFMarker

#EOF
