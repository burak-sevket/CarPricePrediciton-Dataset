from bs4 import BeautifulSoup #veri çekme
import re
import numpy as np
import time
import concurrent.futures
import pandas as pd #yazım
import requests #istek
import sys
from pprint import pprint

headers = ["Fiyat", "Marka", "Seri", "Model", "Yıl", "Yakıt Tipi", "Vites Tipi", "Motor Gücü", "Motor Hacmi", "Kilometre", "Boya-değişen"]
referral = "https://www.arabam.com"
thread_number = int(sys.argv[1])
header = {'User-agent': 'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.16 Safari/537.36'}	
#bunu girmezsek siteye Pythondan baglandıgımız gittigi için
# site bota karsı savunma mekanizmasını aşmak için kendimizi legit user gibi gösteriyoruz


def multi_threaded_execution(url_list):
	results = list()
	for i, link in enumerate(url_list):
		try:
			ret_val = parse_car_info(link)
			if ret_val:
				results.append(ret_val)
				pprint(ret_val)
			print(f"[{length_of_pages - (i*thread_number)}]//Parsed value for: {link}")
		except Exception as e:
			print(e)
			continue
		time.sleep(0.1)
	return results

def parse_car_info(url):
	details = 	{
		"Fiyat" : 0,
		"Marka" : "Belirtilmemiş",
		"Seri" : "Belirtilmemiş",
		"Model" : "Belirtilmemiş",
		"Yıl" : 0,
		"Yakıt Tipi" : "Belirtilmemiş",
		"Vites Tipi" : "Belirtilmemiş", 
		"Motor Gücü" : 0,
		"Motor Hacmi" : 0,
		"Kilometre" : 0,
		"Boya-değişen" : "Belirtilmemiş"
	}

	r = requests.get(url, headers=header) #istek formu
	source = r.text
	soup = BeautifulSoup(source, "html.parser") #Kazım	
	table = soup.find("div", class_="banner-column-detail") #verinin alınacağı alan
	price = table.find(class_="color-red4 font-default-plusmore bold fl").text.strip() # Fiyat alanının konumu
	details["Fiyat"] = int(price[:price.index(" ")].replace(".", ""))
	rows = table.find_all(class_="bcd-list-item")[2:]	# we skip first two, ilan no ve tarihi gereksiz
	pairs = list()
	
	for row in rows:
		_pairs = row.find_all(class_="bli-particle")
		if len(_pairs):
			pairs.append([_pairs[0].text.strip().replace(":", ""), _pairs[1].text.strip()])

	for key, value in pairs:
		# ["Fiyat", "Marka", "Seri", "Model Yıl", "Yakıt Tipi", "Vites Tipi", "Motor Gücü", "Motor Hacmi", "Kilometre", "Boya-değişen"]
		if key in headers: #Tablodaki veriler belli bir standarta göre verildiği için sıralama bu şekilde veri alınabilmektedir.
			if key == "Kilometre":
				value = int(value[:value.index(" ")].replace(".", ""))
			if key == "Motor Hacmi":
				value = value[:value.index(" ")]
				if value.count(".") > 0:
					value = value.replace(".", "")
				value = int(value)
			if key == "Motor Gücü":
				value = value[:value.index(" ")]
				if value.count(".") > 0:
					value = value.replace(".", "")
				value = int(value)
			if key == "Yakıt Tipi" and value not in ["LPG", "Benzin", "Dizel", "LPG & Benzin"]: #Bunlar dışında veri girişi olursa isteği bir sonraki isteğe geçeririz.
				return False
			if key == "Vites Tipi" and value not in ["Düz", "Otomatik", "Yarı Otomatik"]:
				return False
			if key == "Yıl":
				value = int(value)
			details[key] = value
	return details

def main():		
	## Categorized pull.
	global length_of_pages
	start_time = time.time()
	url_list = list()

	print("Checking for url_list.txt")
	try:
		with open("url_list.txt", "r") as f:
			print("Found the url_list file")
			for line in f.readlines():
				try:
					url_list.append(line[:line.index("\n")])
				except ValueError:
					url_list.append(line)	
		
	except FileNotFoundError:
		print("url_list.txt doesn't exists getting url_list from web. Through requests...")
		
		r = requests.get(f"https://www.arabam.com/ikinci-el/otomobil", headers=header)
		source = r.text
		soup = BeautifulSoup(source, "html.parser")
		match = soup.find (class_="category-facet")
		category_links = list()
		
		for item in match.find_all("li", class_="category-facet-selection-item inside-li"):
			category_links.append(referral + item.find("a")["href"] + "?take=50")
		
		with open("url_list.txt", "w") as f:
			for category_link in category_links:
				page = 1
				r = requests.get(category_link, headers=header)
				source = r.text
				soup = BeautifulSoup(source, "html.parser")
				paging_elements = soup.find(id="pagination").find("ul", class_="pagination").find_all("li")
				last_page = int(paging_elements[-2].text)
				print(f"Parsing For Category: {category_link}\nNumber of Pages: {last_page}")
				while page <= last_page:
					r = requests.get(category_link + f"&page={page}", headers=header)
					source = r.text
					soup = BeautifulSoup(source, "html.parser")
					match = soup.find(id="main-listing")
					items = soup.find_all(class_="listing-list-item pr should-hover bg-white")
					for item in items:
						link = referral + item.find("a")["href"]
						f.write(link + "\n")
						url_list.append(link)

					print("Finished Page: ", page)
					page += 1

	length_of_pages = len(url_list)
	print(f"Creating {thread_number} threads to parse each car info.")

	executor = concurrent.futures.ThreadPoolExecutor() # Or ProcessPoolExecutor
	splitted_data = np.array_split(url_list, thread_number)
	#[[url list], [ url list]]
	# Threadleri eş sayıya böler örnek 4 tane Linki 3 threade 2 - 1 - 1 olarak bölüyor

	results = executor.map(multi_threaded_execution, splitted_data)

	finals = []
	for pack in results:
		finals += pack

	print("Parsing data ended in:", time.time() - start_time, "--- For Number of Links: ", len(url_list))

	print("Creating data frame.")
	df = pd.DataFrame(finals)
	print("Exporting the data frame as output.csv")
	df.to_csv("output.csv", index=False, sep=",", header=True, encoding="utf-16")
	print("Exporting finished. Program ended.")

if __name__ == '__main__':
	main()