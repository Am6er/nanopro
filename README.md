# nanopro
KB Radar Atom Spectra shproto protocol

Worked on Mac OS, Linux, Windows..

Requirements:
`pip3 install pyserial`

Type "help" for help:

    Some non-hazardous commands for text mode:
        -inf
            Prints debug information and variables
        -sta
            Starts collecting impulses for histogram
        -sto
            Stops collecting impulses for histogram
        -rst
            Resets collecting
        -nos <number>
            Sets number adc value for peak detection (default value - 30).
            Lower number (for ex 12) - lowest energies peaks collected to histogram.
            
    Other common commands:
        spec_sta
            Start saving spectra to file
        spec_sto
            Stop saving spectra to file
        stat
            Show statistics while spectra gathering
        quit or exit
            Exits terminal