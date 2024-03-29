#! /usr/local/bin/python3
"""
Read ccs811 bme280 tmp117 sensors, and send to CHORDS.
"""

# pylint: disable=C0103

import time
import sys
import json

import iwconfig
import pychords.tochords as tochords

import airq

# A test config to be used in the absence of a configuration file
test_config = """
{
    "chords": {
        "skey":    "secret_key",
        "host":    "chords_host.com",
        "enabled": true,
        "inst_id": "1",
        "test":    false
    },
    "airq": {
      "ccs811_i2c": 91,
      "bme280_i2c": 119,
      "tmp117_i2c": 72,
      "ccs811_n_samples": 60,
      "report_interval": 60
    }
}
"""

def make_chords_vars(old_hash, replace_keys):
    """
    Rename the keys in a hash. If an old key does not
    exist in the new_keys, remove it.
    """
    new_hash = {}
    for old_key, old_val in old_hash.items():
        if old_key in replace_keys:
            new_hash[replace_keys[old_key]] = old_val

    # The chords library wants the vars in a separate dict
    new_hash = {"vars": new_hash}
    return new_hash


def timestamp():
    """
    Return an ISO formated current timestamp
    """
    t = time.gmtime()
    ts = "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}Z".format(t[0], t[1], t[2], t[3], t[4], t[5])
    return ts

def get_iw():
    """
    Return iwconfig values that we want to send on to CHORDS.
    Possible returned hash values are "sig_dbm".
    """
    iw = iwconfig.iwconfig()
    iwvars = {}
    if "sig_dbm" in iw.keys():
        iwvars["sig_dbm"] = iw["sig_dbm"]
    return iwvars

if __name__ == '__main__':

    new_keys = {
        'time': 'at',
        'tvoc_ppb': 'tvoc',
        'tvoc_std': 'tvoc_std',
        'eco2_ppm': 'eco2',
        'eco2_std': 'eco2_std',
        'pres_mb': 'pres',
        'tdry_degc': 'tdry',
        'rh': 'rh',
        'n':'n'
    }

    print("Starting", sys.argv)

    if len(sys.argv) > 2:
        print("Usage:", sys.argv[0], "[config_file]")
        sys.exit(1)

    if len(sys.argv) == 1:
        config = json.loads(test_config)
    else:
        config = json.loads(open(sys.argv[1]).read())

    print(config['airq'])

    # Extract some useful config values
    host = config["chords"]["host"]

    chords_options = {
        "inst_id": config["chords"]["inst_id"],
        "test": config["chords"]["test"],
    }
    if "skey" in config["chords"]:
        chords_options["skey"] = config["chords"]["skey"]
    if ("api_email" in config["chords"]) and ("api_key" in config["chords"]):
        chords_options["api_email"] = config["chords"]["api_email"]
        chords_options["api_key"] = config["chords"]["api_key"]

    ccs811_i2c = config["airq"]["ccs811_i2c"]
    bme280_i2c = config["airq"]["bme280_i2c"]
    tmp117_i2c = config["airq"]["tmp117_i2c"]
    ccs811_n_samples = config["airq"]["ccs811_n_samples"]
    chords_report_interval = config["airq"]["chords_report_interval"]

    device = airq.airq(
      ccs811_address=ccs811_i2c, 
      bme280_address=bme280_i2c, 
      tmp117_address=tmp117_i2c,
      ccs811_n_samples=ccs811_n_samples)

    # Start the CHORDS sender thread
    tochords.startSender()

    # Flush the outputs
    sys.stdout.flush()
    sys.stderr.flush()

    while True:
        # Sleep until the next measurement time
        time.sleep(chords_report_interval)

        # Get the CCS811 reading
        ccs811_data = device.reading()
        ccs811_data['time'] = timestamp()

        # Make a chords variable dict to send to chords
        chords_record = make_chords_vars(ccs811_data, new_keys)

        # Add in other variables

        # Get iwconfig details
        iw_vars = get_iw()
        chords_record["vars"].update(iw_vars)

        # Merge in the chords options
        chords_record.update(chords_options)

        # create the chords uri
        uri = tochords.buildURI(host, chords_record)
        print(uri)
        # Send it to chords
        tochords.submitURI(uri, 10*24*60)

        # Flush the outputs
        sys.stdout.flush()
        sys.stderr.flush()

