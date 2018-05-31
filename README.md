[![Docker Pulls](https://img.shields.io/docker/pulls/stanfordcni/pfile-mr-classifier.svg)](https://hub.docker.com/r/stanfordcni/pfile-mr-classifier/)
[![Docker Stars](https://img.shields.io/docker/stars/stanfordcni/pfile-mr-classifier.svg)](https://hub.docker.com/r/stanfordcni/pfile-mr-classifier/)

# stanfordcni/pfile-mr-classifier
Build context for a [Flywheel Gear](https://github.com/flywheel-io/gears/tree/master/spec) that uses [pfile_tools](https://github.com/njvack/pfile-tools) to extract classification information from GE P-Files.

### Example Usage
```
   docker run --rm -ti \
        -v /path/to/pfile/data:/flwheel/v0/input/pfile \
        -v /path/to/output:/flwheel/v0/output \
        stanfordcni/pfile-mr-classifier \
```
