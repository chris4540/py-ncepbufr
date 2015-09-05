import ncepbufr
import numpy as np
from netCDF4 import Dataset
from prepbufr_mnemonics import mnemonics_dict
import sys

prepbufr_filename = sys.argv[1]
netcdf_filename = sys.argv[2]
if prepbufr_filename == netcdf_filename:
    raise IOError('cannot overwrite input prepbufr file')

hdstr='SID XOB YOB DHR TYP ELV SAID T29'
obstr='POB QOB TOB ZOB UOB VOB PWO MXGS HOVI CAT PRSS TDO PMO'
qcstr='PQM QQM TQM ZQM WQM PWQ PMQ'
oestr='POE QOE TOE NUL WOE PWE'

# read prepbufr file, write data to netcdf file.

nc = Dataset(netcdf_filename,'w',format='NETCDF4')
hd = nc.createDimension('header',len(hdstr.split())-1)
ob = nc.createDimension('obinfo',len(obstr.split()))
oe = nc.createDimension('oeinfo',len(oestr.split()))
qc = nc.createDimension('qcinfo',len(qcstr.split()))
nm = nc.createDimension('msg',None)
msg_date =\
nc.createVariable('msg_date',np.int32,('msg',),zlib=True,fill_value=-1)
msg_date.info = 'BUFR MESSAGE DATE'
tank_date =\
nc.createVariable('tank_date',np.int32,('msg',),zlib=True,fill_value=-1)
tank_date.info = 'BUFR TANK RECEIPT DATE'
nlevs = nc.createDimension('nlevs',200)

bufr = ncepbufr.open(prepbufr_filename)
while bufr.advance() == 0: # loop over messages.
    g = nc.createGroup(bufr.msg_type)
    nmsg = bufr.msg_counter
    msg_date[nmsg] = bufr.msg_date
    if bufr.receipt_time is not None:
        tank_date[nmsg] = bufr.receipt_time
    else:
        tank_date[nmsg] = -1
    if not g.variables.has_key('obdata'):
        g.setncattr('desc',mnemonics_dict[bufr.msg_type].rstrip())
        nobs = g.createDimension('nobs',None)
        hdrdata =\
        g.createVariable('header',np.float32,('nobs','header'),zlib=True,fill_value=bufr.missing_value)
        stnid = g.createVariable('stationid',str,('nobs',))
        stnid.info = 'STATION IDENTIFICATION'
        msgnum = g.createVariable('msgnum',np.int32,('nobs',))
        msgnum.info = 'BUFR MESSAGE NUMBER'
        for key in hdstr.split()[1:]:
            hdrdata.setncattr(key,mnemonics_dict[key])
        hdrdata.info = hdstr[4:]
        if bufr.msg_type in ['RASSDA','VADWND','PROFLR','ADPUPA']:
            obdata =\
            g.createVariable('obdata',np.float32,('nobs','nlevs','obinfo'),zlib=True,fill_value=bufr.missing_value)
            oedata =\
            g.createVariable('oberr',np.float32,('nobs','nlevs','oeinfo'),zlib=True,fill_value=bufr.missing_value)
            qcdata =\
            g.createVariable('qcinfo',np.float32,('nobs','nlevs','qcinfo'),zlib=True,fill_value=bufr.missing_value)
        else:
            obdata = g.createVariable('obdata',np.float32,('nobs','obinfo'),zlib=True)
            oedata = g.createVariable('oberr',np.float32,('nobs','oeinfo'),zlib=True)
            qcdata = g.createVariable('qcinfo',np.float32,('nobs','qcinfo'),zlib=True)
        for key in obstr.split():
            obdata.setncattr(key,mnemonics_dict[key])
        obdata.info = obstr
        for key in oestr.split():
            oedata.setncattr(key,mnemonics_dict[key])
        oedata.info = oestr
        for key in qcstr.split():
            qcdata.setncattr(key,mnemonics_dict[key])
        qcdata.info = qcstr
    while bufr.load_subset() == 0: # loop over subsets in message.
        hdr = bufr.read_subset(hdstr).squeeze()
        obs = bufr.read_subset(obstr)
        qc  = bufr.read_subset(qcstr)
        err = bufr.read_subset(oestr)
        n = obs.shape[-1]
        nob = g['header'].shape[0]
        g['header'][nob] = hdr.squeeze()[1:]
        id = hdr[0].tostring()
        g['stationid'][nob] = id
        g['msgnum'][nob] = bufr.msg_counter
        if bufr.msg_type in ['RASSDA','VADWND','PROFLR','ADPUPA']:
            g['obdata'][nob,:n] = obs.T
            g['oberr'][nob,:n]  = err.T
            g['qcinfo'][nob,:n] = qc.T
        else:
            g['obdata'][nob] = obs.squeeze()
            g['oberr'][nob]  = err.squeeze()
            g['qcinfo'][nob] = qc.squeeze()
    nc.sync()

bufr.close()
nc.close()
