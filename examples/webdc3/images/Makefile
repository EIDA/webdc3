RESIZE=-resize 120x48

eida-logo2.png: eida-orfeus3.jpg
	# Adjust to 2.5:1 for 120x48, and remove text underneath:
	convert -crop 540x216+0+24 eida-orfeus3.jpg ${RESIZE} eida-logo2.png

eida-orfeus3.jpg:
	wget "http://www.orfeus-eu.org/eida/eida-orfeus3.jpg"

clean:
	-rm eida-logo2.png
	-rm eida-orfeus3.jpg

