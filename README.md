# Winston
Winston is URN's dead air detection and rectification tool

## Background
URN uses RCS Zetta as its primary playout system, with two main computers sharing the playout role in a "hotspare pair" - that is we switch between the two depending on if the studio is in use or automated programming is running. The most common source of dead air in a setup like this is presenters forgetting to switch back to the automation stream upon finishing a show, leading to the studio stream running out of music. 

## Solution
Winston listens into the main URN web stream and, upon silence being detected, sends GPIO messages to our Zetta sequencing server to indicate that it should switch to the automation computer and play the next track. It will also send messages via a webhook to a Discord channel, informing the technical team of the switchover. 

## Installation and Setup
Installation and setup details coming soon!
