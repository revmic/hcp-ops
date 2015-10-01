from hcpxnat.interface import HcpInterface
import ConfigParser

from app import app

config = ConfigParser.ConfigParser()
config.read('/Users/michael/.hcprestricted')

cdb = HcpInterface(url=config.get('hcpxnat', 'site'),
                   username=config.get('hcpxnat', 'username'),
                   password=config.get('hcpxnat', 'password'))


