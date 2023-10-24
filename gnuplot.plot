set datafile separator ','
set ylabel 'Counts'
set xlabel 'Channel'

plot "spectrum.csv" using 1:($2 < 1 ? $2 : log10($2)) with lines
