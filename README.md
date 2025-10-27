# metsearch
GUI for searching the The Metropolitan Museum of Art API.

## Executables

The executables can be found under the `dist` directory.\
The platform-specific executable files are:
* Windows: `metsearch-gui.exe`
* Linux: `metsearch-gui`

Double-click the appropriate executable for your platform to run the app.

### MacOS

Sadly I didn't have access to a Mac machine, so I couldn't compile an 
executable for MacOS. \
That said, perhaps the Linux executable will work on MacOS?

## Known issues and limitations

### Minute-long cycles for processing requests

The service keeps track of how many requests we make per minute. 
Once we hit 80, the service responds with AccessDenied for each request, 
until a minute has elapsed. This is part of the business logic of the service 
and is unavoidable.

For our tool, it means that we have batch the requests, that is, 
to process 80 requests at a time, and then wait until a minute has elapsed 
before continuing processing requests.

That is why there is a countdown displayed at the bottom left of the UI, 
so that we get a sense of how long we have to wait until more requests 
are processed.

### Classification

I initially had widgets for filtering by classification, but eventually 
learned that the service API isn't well equipped to support this. \

The issue is that the service doesn't have an endpoint to tell us what are
all the available classifications. So, the only way to discover them is 
to extract them from the object documents that we have. \

Since we're only getting 80 documents at a time, it means the classifications
could grow as we get more and more documents. Technically there's nothing 
wrong with this, but it's a bizarre experience and I decided to lave it out
in the interest of time.