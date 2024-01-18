#! /usr/bin/python3.11

from struct import *
import binascii



#coeff = [ -8.5, 0.3827, 2.127e-06, 0, 0 ]
# coeff = [ -3.22721, 0.365377, 1.15403E-05, -1.13138E-09, 0 ]
# coeff = [ -3.10327, 0.368445, 9.2457E-06, -8.52471E-10, 0 ]
# coeff = [ -3.50753, 0.369576, 8.31747E-06, -7.33575E-10, 0 ]
#coeff =   [ -5.81279, 0.37369,  6.0335E-06, -4.51995E-10, 0 ] # nos14 rise7 fall8 srise3 prise8 pfall0 sfall0 stdTHR
coeff =   [-7.80666, 0.37386, 6.23949E-06, -4.57829E-10, 0 ]   # nos14 rise7 fall8 srise30 prise8 pfall0 sfall0 MyTHR2


str = ''
r_n = 0
i = 0
c_b = [ pack('d', 0.) ] * 12
s = ''
for  v in coeff:
	c_b[i] = pack('d', coeff[i])
	vv = unpack('II', c_b[i])
	s += "%08X" % (vv[1])
	# print(coeff[i], vv)
	print("-cal {} {:08X}".format(r_n, vv[1]))
	s += "%08X" % (vv[0])
	r_n += 1
	print("-cal {} {:08X}".format(r_n, vv[0]))
	r_n += 1
	i += 1

# print(s)
crc = binascii.crc32(bytearray(s, "ascii")) % 2**32


# print(s, crc)
print("-cal {} {:08X}".format(r_n, crc))

