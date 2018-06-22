#!/usr/bin/env python

import os
import re
import json
import pytz
import string
import tzlocal
import logging
import zipfile
import datetime
import classification_from_label
from pprint import pprint

logging.basicConfig()
log = logging.getLogger('pfile-mr-classifier')

def get_pfile_classification(pfile):
    """
    Determine pfile classification from series description, etc.
    """
    classification = {}
    classification = classification_from_label.infer_classification(pfile.series_description)

    # If this is multi-band, note that, if this is a muxarcepi as well, use
    # custom MUXRECON classification. This denotes that we should use muxrecon.
    if pfile.rh_user_6 > 1:
        if classification.has_key('Features'):
            classification['Features'].append('Multi-Band')
        else:
            classification['Features'] = ['Multi-Band']
        if pfile.psd_name == 'muxarcepi':
            if classification.has_key('Custom'):
                classification['Custom'].append('MUXRECON')
            else:
                classification['Custom'] = ['MUXRECON']

    return classification


def validate_timezone(zone):
    """
    Validate the timezone
    """
    if zone is None:
        zone = tzlocal.get_localzone()
    else:
        try:
            zone = pytz.timezone(zone.zone)
        except pytz.UnknownTimeZoneError:
            zone = None
    return zone


def parse_patient_age(age):
    """
    Parse patient age from string.
    convert from 70d, 10w, 2m, 1y to datetime.timedelta object.
    Returns age as duration in seconds.
    """
    if age == 'None' or not age:
        return None
    else:
        age = str(age)

    conversion = {  # conversion to days
        'Y': 365,
        'M': 30,
        'W': 7,
        'D': 1,
    }
    scale = age[-1:]
    value = age[:-1]
    if scale not in conversion.keys():
        # Assume years
        scale = 'Y'
        value = age

    age_in_seconds = datetime.timedelta(int(value) * conversion.get(scale)).total_seconds()

    # Make sure that the age is reasonable
    if not age_in_seconds or age_in_seconds <= 0:
        age_in_seconds = None

    return age_in_seconds


def get_timestamp(pfile, timezone):
    """
    Parse Study Date and Time, return acquisition and session timestamps
    """
    session_timestamp = pfile.exam_datetime
    acquisition_timestamp = pfile.series_datetime

    if session_timestamp:
        if session_timestamp.tzinfo is None:
            log.info('no tzinfo found for session timestamp - using %s' % timezone)
            session_timestamp = timezone.localize(session_timestamp)
        session_timestamp = session_timestamp.isoformat()
    else:
        session_timestamp = ''
    if acquisition_timestamp:
        if acquisition_timestamp.tzinfo is None:
            log.info('no tzinfo found for acquisition timestamp - using %s' % timezone)
            acquisition_timestamp = timezone.localize(acquisition_timestamp)
        acquisition_timestamp = acquisition_timestamp.isoformat()
    else:
        acquisition_timestamp = ''
    return session_timestamp, acquisition_timestamp


def get_sex_string(sex_str):
    """
    Return male or female string.
    """
    if sex_str == 1:
        sex = 'male'
    elif sex_str == 2:
        sex = 'female'
    else:
        sex = 'unknown'
    return sex


def extract_pfile_header(pfile_header_csv):
    """
    Extract pfile header from csv
    """
    import csv
    pfile_header = {}
    with open(pfile_header_csv, 'r') as csvfile:
        csvreader = csv.reader(csvfile)

        # This skips the first row of the CSV file.
        next(csvreader)
        for row in csvreader:
            if row[1]:
                try:
                    row[1] = int(row[1])
                except:
                    try:
                        row[1] = float(row[1])
                    except:
                        pass
                pfile_header[row[0]] = row[1]

    return pfile_header


def pfile_classify(pfile, pfile_header_csv, pfile_name, outbase, timezone):
    """
    Extracts metadata from pfile file header within a zip file and writes to .metadata.json.
    """
    from pfile_tools import headers
    import csv
    import json

    # Check for input file path
    if not os.path.exists(pfile_header_csv):
        log.debug('could not find %s' %  pfile_header_csv)
        os.exit(1)

    if not outbase:
        outbase = '/flywheel/v0/output'
        log.info('setting outbase to %s' % outbase)

    # Grab the pfile_header from the csv
    pfile_header = extract_pfile_header(pfile_header_csv)
    _pfile = headers.Pfile.from_file(pfile)

    # Get timestamps
    session_timestamp, acquisition_timestamp = get_timestamp(_pfile, timezone);

    # Build metadata
    metadata = {}

    # Session metadata
    metadata['session'] = {}
    metadata['session']['operator'] = _pfile.operators_name
    metadata['session']['label'] = str(_pfile.exam_number)
    if session_timestamp:
        metadata['session']['timestamp'] = session_timestamp


    # Subject Metadata
    metadata['session']['subject'] = {}
    metadata['session']['subject']['sex'] = get_sex_string(_pfile.patient_sex)
    age = parse_patient_age(_pfile.patient_age)
    metadata['session']['subject']['age'] = int(age) if age else 0
    subname = _pfile.patient_name
    if subname:
        name = subname.split('^')
        metadata['session']['subject']['lastname'] = name[0]
        if len(name) == 2:
            metadata['session']['subject']['firstname'] = name[1]


    # File metadata
    pfile_file = {}
    pfile_file['name'] = os.path.basename(pfile_name)
    pfile_file['modality'] = _pfile.exam_type
    pfile_file['classification'] = get_pfile_classification(_pfile)
    pfile_file['info'] = extract_pfile_header(pfile_header_csv)


    # Acquisition metadata
    metadata['acquisition'] = {}
    metadata['acquisition']['instrument'] = _pfile.system_id
    metadata['acquisition']['label'] = _pfile.series_description
    if acquisition_timestamp:
        metadata['acquisition']['timestamp'] = acquisition_timestamp

    # Append the pfile_file to the files array
    metadata['acquisition']['files'] = [pfile_file]

    # Write out the metadata to file (.metadata.json)
    metafile_outname = os.path.join(outbase,'.metadata.json')
    with open(metafile_outname, 'w') as metafile:
        json.dump(metadata, metafile)

    # Show the metadata
    pprint(metadata)

    return metafile_outname


if __name__ == '__main__':
    """
    Generate session, subject, and acquisition metatada by parsing the pfile header, using pfile_tools.
    """
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('pfile_name', help='pfile_name')
    ap.add_argument('pfile', help='path to pfile header')
    ap.add_argument('pfile_csv', help='path to pfile header csv')
    ap.add_argument('outbase', nargs='?', help='outfile name prefix')
    ap.add_argument('--log_level', help='logging level', default='info')
    args = ap.parse_args()

    log.setLevel(getattr(logging, args.log_level.upper()))
    logging.getLogger('pfile').setLevel(logging.INFO)
    log.info('start: %s' % datetime.datetime.utcnow())

    args.timezone = validate_timezone(tzlocal.get_localzone())
    print(args.timezone)

    metadatafile = pfile_classify(args.pfile, args.pfile_csv, args.pfile_name, args.outbase, args.timezone)

    if os.path.exists(metadatafile):
        log.info('generated %s' % metadatafile)
    else:
        log.info('failure! %s was not generated!' % metadatafile)

    log.info('stop: %s' % datetime.datetime.utcnow())
