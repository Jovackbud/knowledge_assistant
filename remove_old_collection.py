from pymilvus import connections, utility

# connect to your Milvus
connections.connect(alias="default", host="localhost", port="19530")

# drop the old collection and all its data
utility.drop_collection("adv_rbac_kb_v1")
