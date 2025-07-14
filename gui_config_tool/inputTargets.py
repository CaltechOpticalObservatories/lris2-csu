'''
the file format is a starlist: https://www2.keck.hawaii.edu/observing/starlist.html

'''

import numpy as np


keywords = (
    "pmra",
    "pmdec",
    "dra",
    "ddec",
    "vmag",
    "rotmode",
    "rotdest",
    "wrap",
    "raoffset",
    "decoffset"
    )

class TargetList:

    def __init__(self,file_path):

        self.file_path = file_path
        '''
        reads a starlist file and returns a list [name: Ra,Dec,equinox,[other]]
        '''
        self.target_list = []
        with open(self.file_path) as file:
            for line in file:
                if line[0] != "#" and line.split():
                    
                    name = line[0:15].rstrip() #gets the name
                    line = line.replace(line[0:15],"") #removes the name from the line
                    line = line.replace(line[line.find("#"):],"") #takes out any end comments

                    line = line.split(" ") #seperates all the items in the list
                    line = [x for x in line if x != ""]#takes out all the extra spaces
                    
                    Ra = "".join(x+" " for x in line[0:3]).strip() #defines the Ra
                    Dec = "".join(x+" " for x in line[3:6]).strip() #defines the Dec
                    equinox = line[6] #defines the equinox
                    
                    del line[:7] #deletes the ra, dec, and equinox from the list
                    if line == []: del line #deletes empty lists

                    try:
                        self.target_list.append([name,Ra,Dec,equinox,line]) #add the Ra, Dec, and equinox to the dicitonary
                    except:
                        self.target_list.append([name,Ra,Dec,equinox])

    def send_list(self):
        return self.target_list






