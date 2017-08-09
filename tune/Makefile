all:    text edit

text: edit.txt
	python edit_mode.py < edit.txt > /tmp/edit.ly

edit: text
	lilypond -o /tmp/edit /tmp/edit.ly

clean:
	rm -f /tmp/edit.ly /tmp/edit.midi /tmp/edit.pdf

