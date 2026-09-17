# boinc-fleet
A small app for monitoring multiple nodes running volunteer computing through BOINC.


## Description

Berkeley Open Infrastructure for Network Computing (BOINC) is a system created by the University of California, Berkeley to support large-scale volunteer computing (where anyone on the internet can sign up their device to perform computing work) in order to advance scientific research. Different research institutions register projects on BOINC (e.g., MilkyWay@Home, Asteroids@Home) and schedule computing in the form of work units, which can be downloaded and worked on by volunteer computers. I personally use `boinc` on the devices in my home network, but I have found tracking progress across devices and especially headless nodes without the GUI app to be difficult.

This project is intended to be a small service that shows live progress and other statistics across a number of BOINC nodes on a single, locally-hosted web page, by talking to the BOINC GUI RPC protocol directly. I am viewing this as a project to continue my skills development (e.g., TCP, polling, web servers, etc.) while hopefully producing a utility I will actually find useful.
