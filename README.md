*проект заморожен, используйте новую версию* https://github.com/kib888/ptaf-pro-conf_ansible/


#### PT AF pro configurator

Конфигуратор (скрипт python) работает по принципу: на входе заполняете Excel с сетевыми параметрами, на выходе получаете набор bash команд для конфигурации кластера.

Скрипт Python не следует выполнять на самих серверах AF, лучше на отдельной машине. Использовать последнюю версию Python.
Для работы скрипта необходимо доставить в Python пакеты:
```
pip install ipcalc
pip install six
pip install pandas
pip install openpyxl
```
Далее:
1. Заполняется таблица Excel (`af-pro-configurator.xlsx`).
1. Запускается Python-скрипт (`af-pro-configurator.py`).
1. В директории создается файл с инструкцией и командами для настройки и инсталляции AF, с паролями и ссылками.

по ошибкам можно писать в https://t.me/krant0r
