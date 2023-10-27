set datafile separator ','
set xlabel 'Channel'
set lmargin 10
set bmargin 3
set rmargin 10
set tmargin 1
set size ratio 0.5625
set xrange [0:8192]

set multiplot

set log y
set ytics nomirror
unset y2tics
set key left
plot "spectrum.csv" using 1:($2) with lines lc rgb 'blue' title "log"

unset log y
unset ytics
set y2tics
set key right
plot "spectrum.csv" using 1:($2) axis x1y2 with lines lc rgb 'magenta' title "lin"
unset multiplot
