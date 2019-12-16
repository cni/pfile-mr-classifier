# stanfordcni/pfile-mr-classifier
#

FROM ubuntu:xenial

MAINTAINER Michael Perry <lmperry@stanford.edu>

# Install dependencies
RUN apt-get update && apt-get -y install \
    python \
    python-dev \
    python-pip \
    jq \
    git \
    unzip \
    tzdata \
    wget

# Install Pip libs
RUN pip install \
  numpy==1.15.1 \
  python-dateutil==2.6.0 \
  pytz==2017.2 \
  tzlocal==1.4 \
  nibabel==2.2.1

# Install pfile_tools
WORKDIR /opt
ENV COMMIT 8089e427f66fc136aed32b3039f13f739f9dc521
RUN git clone https://github.com/cni/pfile-tools.git && \
      cd pfile-tools && \
      git checkout ${COMMIT} && \
      python setup.py install

# Make directory for flywheel spec (v0)
ENV FLYWHEEL /flywheel/v0
WORKDIR ${FLYWHEEL}
COPY run ${FLYWHEEL}/run
COPY manifest.json ${FLYWHEEL}/manifest.json

# Add code to determine classification from acquisitions descrip (label)
COPY classification_from_label.py classification_from_label.py

# Copy classifier code into place
COPY pfile-mr-classifier.py ${FLYWHEEL}/pfile-mr-classifier.py

# Set the entrypoint
ENTRYPOINT ["/flywheel/v0/run"]
