#tecancavro

Python package to control Tecan Cavro Syringe pumps.

Modules are provided for:

- Tecan OEM API communication frame construction/parsing ([tecanapi.py](https://github.com/benpruitt/tecancavro/blob/master/tecancavro/tecanapi.py) --> `class: APILink`)<br>
- Serial wrapped Tecan OEM API communication ([transport.py](https://github.com/benpruitt/tecancavro/blob/master/tecancavro/tecanapi.py) --> `class: SerialAPILink`)<br>
- Generic syringe control ([syringe.py](https://github.com/benpruitt/tecancavro/blob/master/tecancavro/syringe.py) --> `class: Syringe`)<br>
- Specific Cavro model control (with high level funcitons) [models.py](https://github.com/benpruitt/tecancavro/blob/master/tecancavro/models.py)<br>
  - XCALIBUR with distribution valve (`class: XCaliburD`)

###Work in progress :: not stable

