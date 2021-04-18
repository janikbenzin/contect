from typing import Union, Type

from contect.available.available import AvailableDetectors
from contect.deviationdetection.detectors.adar.detector import ADARDetector
from contect.deviationdetection.detectors.alignments.detector import AlignmentsDetector
from contect.deviationdetection.detectors.autoencoder.detector import AutoencDetector
from contect.deviationdetection.detectors.profiles.detector import ProfilesDetector
from contect.deviationdetection.objects.detection import DetectorParameters


def get_detector(variant: AvailableDetectors,
                 param: DetectorParameters) -> Union[ProfilesDetector,
                                                     AlignmentsDetector,
                                                     ADARDetector,
                                                     AutoencDetector]:
    if variant is AvailableDetectors.PROF:
        return ProfilesDetector(param.param)
    elif variant is AvailableDetectors.ALIGN:
        return AlignmentsDetector(param.param)
    elif variant is AvailableDetectors.ADAR:
        return ADARDetector(param.param)
    elif variant is AvailableDetectors.AUTOENC:
        return AutoencDetector(param.param)
