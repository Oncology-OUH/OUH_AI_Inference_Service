from pynetdicom import AE, evt, AllStoragePresentationContexts, ALL_TRANSFER_SYNTAXES
import logging, logging.handlers

def setup_logging() -> None:
    """
    Sets up logging.
    """
    logging_level = 'DEBUG'
    logging_format = "[%(asctime)s] %(levelname)-8s %(name)-12s: %(message)s"
    logging.basicConfig(
        level=logging_level,
        format=logging_format,
        handlers=[
            logging.StreamHandler(),
        ]
    )
    return

class DICOM_info:
    ip_address = None
    port = None
    aet = None

    def __init__(self, ip, port, aet):
        self.ip_address = ip
        self.port = port
        self.aet = aet

class DICOM_receiver:
    info = None
    log = None
    ip_address = None
    port = None
    aet = None

    def __init__(self, info):
        self.log = logging.getLogger("Init")
        self.ip_address = info.ip_address
        self.port = info.port
        self.aet = info.aet

    def receive_DICOM(self):
        """
        Sets up DICOM receiver
        """
        self.log.info("starting up DICOM receiver")

        handlers = [(evt.EVT_C_STORE, self.handle_store)]

        ae = AE()
        storage_sop_classes = [
            cx.abstract_syntax for cx in AllStoragePresentationContexts
        ]

        for uid in storage_sop_classes:
            ae.add_supported_context(uid, ALL_TRANSFER_SYNTAXES)
        ae.start_server(address=(self.ip_address, self.port), ae_title=self.aet,
                        block=True, evt_handlers=handlers)

        return

    def handle_store(self, event):
        """Handle EVT_C_STORE events."""
        ds = event.dataset
        ds.file_meta = event.file_meta
        ds.save_as(ds.SOPInstanceUID, write_like_original=False)

        return 0x0000


if __name__ == '__main__':
    setup_logging()
    info = DICOM_info("127.0.0.1", 11112, "test_receiver")
    receiving_module = DICOM_receiver(info)
    receiving_module.receive_DICOM()






# See PyCharm help at https://www.jetbrains.com/help/pycharm/
