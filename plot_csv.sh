#!/bin/bash
#
# see https://raymii.org/s/tutorials/GNUplot_tips_for_nice_looking_charts_from_a_CSV_file.html

CSV="$1"

# set xtics 10

gnuplot -persist <<-EOFMarker
set terminal wxt size 800,600
set xdata time
set timefmt "%s"
set key autotitle columnhead
set format x "%H:%M"
set xlabel 'Time'
set xtics rotate
set datafile separator ';'
set y2tics
set ytics nomirror
set ylabel "Puls/SpO2"
set y2label "Motions"
plot "$CSV" using 2:7 with linespoints axis x1y2, \
     "" using 2:4 with linespoints, \
     "" using 2:3 with linespoints
EOFMarker

#EOF
