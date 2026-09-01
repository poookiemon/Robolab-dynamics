import os
from rspace_client.inv import inv
from rspace_client.eln import eln

#inv_cli = inv.InventoryClient(os.getenv("RSPACE_URL"), os.getenv("RSPACE_API_KEY"))
#eln_cli = eln.ELNClient(os.getenv("RSPACE_URL"), os.getenv("RSPACE_API_KEY"))

eln_cli = eln.ELNClient("http://eln.med.uni-goettingen.de", "Op6OLkr1z6JdNp2EB6OSu1TFhQ22quKP")
inv_cli = inv.InventoryClient("http://eln.med.uni-goettingen.de", "Op6OLkr1z6JdNp2EB6OSu1TFhQ22quKP")

#print(os.getenv("RSPACE_URL"))
print(eln_cli.get_forms())
print(eln_cli.get_status())

#samples = inv_cli.list_samples()
#print (f"There are {samples['totalHits']} samples")
