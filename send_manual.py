from rental_watch import notify_telegram
text = '''Rent monitor — ručno slanje propuštenih NEW oglasa:

Rent Valley:
https://rentvalley.nl/en/listings/herschelstraat-22-a-den-haag.html
https://rentvalley.nl/en/listings/obrechtstraat-376-b-den-haag.html
https://rentvalley.nl/en/listings/prins-hendrikstraat-95-den-haag.html
https://rentvalley.nl/en/listings/prinsegracht-69-g-den-haag.html
https://rentvalley.nl/en/listings/prinsegracht-69-y-den-haag.html
https://rentvalley.nl/en/listings/prinsegracht-73-l-den-haag.html
https://rentvalley.nl/en/listings/westerbaenstraat-61-d-den-haag.html

Rental Rotterdam (new):
https://www.rentalrotterdam.nl/woningaanbod/huur/den-haag/laakweg/30-v

HAYMAN Rentals:
https://haymanrentals.nl/aanbod/columbusstraat
https://haymanrentals.nl/aanbod/cornelis-jolstraat
https://haymanrentals.nl/aanbod/cornelis-jolstraat-scheveningen
https://haymanrentals.nl/aanbod/daguerrestraat
https://haymanrentals.nl/aanbod/hugo-verrieststraat
https://haymanrentals.nl/aanbod/korte-molenstraat-3
https://haymanrentals.nl/aanbod/prins-hendrikstraat-148a
https://haymanrentals.nl/aanbod/regentesselaan-128b
https://haymanrentals.nl/aanbod/weimarstraat

Kamernet (examples):
https://kamernet.nl/en/for-rent/room-netherlands
https://kamernet.nl/en/for-rent/room-netherlands\
https://kamernet.nl/en/for-rent/rooms-netherlands
https://kamernet.nl/en/for-rent/rooms-netherlands\

Avenir Vastgoed (examples):
https://pl-avenirvastgoed.vercel.app//aanbod/huurwoningen
https://www.avenirvastgoed.com/aanbod/aangekocht
https://www.avenirvastgoed.com/aanbod/huurwoningen
https://www.avenirvastgoed.com/aanbod/koopwoningen
https://www.avenirvastgoed.com/aanbod/transacties

Expat Rentals Holland:
https://www.expatrentalsholland.com/offer/in/den+haag

Homey Housing (images detected):
https://homeyhousing.com/wp-content/uploads/2024/03/woningaanbod-1536x1024.jpg
https://homeyhousing.com/wp-content/uploads/2024/03/woningaanbod-2048x1365.jpg
https://homeyhousing.com/wp-content/uploads/2024/03/woningaanbod.jpg

Frisiamakelaars:
https://frisiamakelaars.nl/en/wonen/aanbod

WoonCompany:
https://wooncompany.nl/woning/den-haag-denneweg-14-g/\
https://wooncompany.nl/woning/den-haag-laan-van-meerdervoort-33/\
https://wooncompany.nl/woning/den-haag-maarsbergenstraat-165-a/\
https://wooncompany.nl/woning/den-haag-noordwal-41/\
https://wooncompany.nl/woning/den-haag-weimarstraat/\
'''
print('sending manual message to Telegram...')
ok = notify_telegram(text)
print('sent=', ok)
