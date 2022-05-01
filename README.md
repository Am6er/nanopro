# nanopro
KB Radar Atom Spectra shproto protocol

Worked on Mac OS, Linux, Windows..

Requirements:
`pip3 install pyserial`

On Debian/Ubuntu add user to input, uucp groups and reboot:
`sudo usermod -aG uucp $USER && sudo usermod -aG input $USER`

On Astra Linux Special Edition add user to dialout group and reboot:
`sudo usermod -aG dialout $USER`



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
        alert_sta
            Alert mode. Start writing individual spectra if cps > cps * ratio
        alert_sto
            Alert mode stop.
        stat
            Show statistics while spectra gathering
        quit or exit
            Exits terminal
        Type serial number to use this device.

Example:

![example usage](image/show.gif)