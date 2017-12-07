# Beehaiv - A simple web API for behavioural experiments

Modern behavioural experiments can run on multiple devices. Some data might be
collected in the lab, using computer running
[PsychToolbox](http://psychtoolbox.org/) or
[PsychoPy](http://www.psychopy.org/), while other data might be collected
online in a browser, using HTML and JavaScript with either
[PsychoJs](https://github.com/psychopy/psychojs) or just using plain
[WebGL](https://get.webgl.org/). The multitude of devices should ideally write
data to one consistent location. Furthermore, data should be accessible in a
consistent way for different experiments. Beehaiv solves this problem by
providing a simple RESTful web API that can run on a separate server and
collect data via web-requests.
