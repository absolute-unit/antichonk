# Antichonk

A tool to help you eliminate chonks on your file system.

## Usage 

Antichonk provides an interactive terminal interface to delete files. 

Run with:

```
sudo python antichonk.py DIRECTORY ORDER_BY(age|size)
```

You will be placed in a REPL where you will be able to perform the following operations
on each file in the directory you specified:

```
Choose from one of these options: 
  d  delete the file
  D  delete the directory which contains the file
  s  skip this file and go on to the next one
  S  skip this directory and go on to the next one
  ?  print this help menu
```
