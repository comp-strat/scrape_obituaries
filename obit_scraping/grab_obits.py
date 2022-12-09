import json
import grab_batch
import os
from tqdm import tqdm

def parse_url_file(filename, root_obits_config, root_directory="all_results", virtual_directory="/media/volume/sdb/test_obits", scrape_id="test", batch_size=30, max_batches=None, start_batch=0):
	url_file = open(filename, "r")
	all_urls = url_file.read().split("\n")
	url_file.close()
	all_urls = [i for i in all_urls if i]

	os.system(f"mkdir -p {root_directory}/{scrape_id} > /dev/null")
	os.system(f"chmod 1777 {root_directory}/{scrape_id} > /dev/null")
	os.system(f"sudo ssh -t -i {root_obits_config['ssh_path']} {root_obits_config['user']}@{root_obits_config['ip']} 'sudo mkdir -p {virtual_directory}/{scrape_id}_obits' > /dev/null")
	os.system(f"sudo ssh -t -i {root_obits_config['ssh_path']} {root_obits_config['user']}@{root_obits_config['ip']} 'sudo chown ubuntu {virtual_directory}/{scrape_id}_obits' > /dev/null")
	os.system(f"sudo ssh -t -i {root_obits_config['ssh_path']} {root_obits_config['user']}@{root_obits_config['ip']} 'sudo chmod 1777 {virtual_directory}/{scrape_id}_obits' > /dev/null")
	end = len(all_urls)
	if not max_batches is None:
		end = batch_size*max_batches
	for i in range(start_batch*batch_size, end, batch_size):
		os.system(f"sudo ssh -t -i {root_obits_config['ssh_path']} {root_obits_config['user']}@{root_obits_config['ip']} 'sudo mkdir -p {root_obits_config['obits_dest_dir']}/{scrape_id}_{i//batch_size}' > /dev/null")
		os.system(f"mkdir -p {root_directory}/{scrape_id}/photos_{i//batch_size} > /dev/null")
		os.system(f"sudo ssh -t -i {root_obits_config['ssh_path']} {root_obits_config['user']}@{root_obits_config['ip']} 'sudo chown ubuntu {root_obits_config['obits_dest_dir']}/{scrape_id}_{i//batch_size}' > /dev/null")
		os.system(f"sudo ssh -t -i {root_obits_config['ssh_path']} {root_obits_config['user']}@{root_obits_config['ip']} 'sudo chmod 1777 {root_obits_config['obits_dest_dir']}/{scrape_id}_{i//batch_size}' > /dev/null")

		batch_photo_config = {
			"ip": root_obits_config["ip"],
			"user": root_obits_config["user"],
			"ssh_path": root_obits_config["ssh_path"],
			"dest_dir": f"{root_obits_config['obits_dest_dir']}/{scrape_id}_{i//batch_size}",
			"send_photos": True,
			"photo_dirname": f"{root_directory}/{scrape_id}/photos_{i//batch_size}"
		}
		batch_urls = all_urls[i:min(i+batch_size, len(all_urls))]
		obit_config = grab_batch.ObitConfig()
		obit_config.photo_config = batch_photo_config
		obit_config.id = scrape_id
		obit_config.low_memory = True
		print(f"Starting batch {i//batch_size}/{end//batch_size}")
		all_obits = grab_batch.batch_scrape(batch_urls, obit_config)
		all_obit_objs = []
		for j in all_obits:
			if not j is None:
				all_obit_objs.append(j.to_obj())
		json_obits = json.dumps(all_obit_objs)
		json_filename = f"{root_directory}/{scrape_id}/obits_{i//batch_size}.json"
		with open(json_filename, "w") as file:
			file.write(json_obits)

		send_cmd = f"sudo scp -qC -o LogLevel=Error -i {root_obits_config['ssh_path']} {json_filename} {root_obits_config['user']}@{root_obits_config['ip']}:{virtual_directory}/{scrape_id}_obits > /dev/null"
		os.system(send_cmd)

def main():
	obits_config_file = open("./obits_config.json")
	root_obits_config = json.load(obits_config_file)
	obits_config_file.close()
	url_file_parts = root_obits_config["scrape_id"].split("_")
	url_file = f"../url_scraping/{url_file_parts[0]}/urllist-{url_file_parts[1]}.txt"
	parse_url_file(url_file, root_obits_config,
		virtual_directory=root_obits_config["obits_dest_dir"]+'/'+root_obits_config["scrape_id"],
		scrape_id=root_obits_config["scrape_id"],
		batch_size=root_obits_config["batch_size"], start_batch=root_obits_config["start_batch"])



if __name__ == '__main__':
	#parse_url_file("../url_scraping/20200101-20200103/urllist-20220502-2319.txt", virtual_directory="/media/volume/sdb", scrape_id="test_azure", batch_size=5, max_batches=3)
	main()

