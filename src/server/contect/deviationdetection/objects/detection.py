from dataclasses import dataclass, field
from typing import Dict, Union

import contect.available.available
from contect.deviationdetection.detectors.adar.detector import ADARDetector
from contect.deviationdetection.detectors.adar.param.config import ADARParameters
from contect.deviationdetection.detectors.alignments.detector import AlignmentsDetector
from contect.deviationdetection.detectors.alignments.param.config import AlignmentsParameters
from contect.deviationdetection.detectors.autoencoder.detector import AutoencDetector
from contect.deviationdetection.detectors.autoencoder.param.config import AutoencParameters
from contect.deviationdetection.detectors.profiles.detector import ProfilesDetector
import contect.available.available as av
from contect.deviationdetection.detectors.profiles.param.config import ProfilesParameters


@dataclass
class DetectorParameters:
    detector: contect.available.available.AvailableDetectors
    param: Union[ProfilesParameters, AlignmentsParameters, ADARParameters, AutoencParameters]


@dataclass
class Detection:
    detector_params: Dict[contect.available.available.AvailableDetectors, DetectorParameters]
    detectors: Dict[contect.available.available.AvailableDetectors, Union[ProfilesDetector,
                                                                          AlignmentsDetector,
                                                                          ADARDetector,
                                                                          AutoencDetector]]
    ca_post_params: Dict[contect.available.available.AvailableDetectors,
                         Dict[av.AvailableSituationType, float]] = field(init=False)
    detector_thresholds: Dict[contect.available.available.AvailableDetectors, float] = field(default_factory=lambda: {})

    def __post_init__(self):
        self.ca_post_params = {
            detector: {typ: 0 for typ in av.AvailableSituationType}
            for detector in self.detector_params
        }

