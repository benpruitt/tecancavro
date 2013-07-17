#tecancavro

Python package to control Tecan Cavro syringe pumps.

Modules are provided for:

- Tecan OEM API communication frame construction/parsing ([tecanapi.py](https://github.com/benpruitt/tecancavro/blob/master/tecancavro/tecanapi.py) --> `class: APILink`)<br>
- Serial wrapped Tecan OEM API communication ([transport.py](https://github.com/benpruitt/tecancavro/blob/master/tecancavro/tecanapi.py) --> `class: SerialAPILink`)<br>
- Generic syringe control ([syringe.py](https://github.com/benpruitt/tecancavro/blob/master/tecancavro/syringe.py) --> `class: Syringe`)<br>
- Specific Cavro model control (with high level functions) [models.py](https://github.com/benpruitt/tecancavro/blob/master/tecancavro/models.py)<br>
  - XCALIBUR with distribution valve (`class: XCaliburD`)

##### **API, serial wrapper, and generic syringe control are all working ([tecanapi.py](https://github.com/benpruitt/tecancavro/blob/master/tecancavro/tecanapi.py), [transport.py](https://github.com/benpruitt/tecancavro/blob/master/tecancavro/tecanapi.py), [syringe.py](https://github.com/benpruitt/tecancavro/blob/master/tecancavro/syringe.py)) 
##### **Model-specific code is working but still evolving

