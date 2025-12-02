import numpy as np
import matplotlib.pyplot as plt
import datetime
import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter
from redmail import EmailSender

for i in range(1, 2):
    # today date
    now = datetime.datetime.now()-datetime.timedelta(days=i)
    format = "%d/%m/%y %H:%M:%S"
    fileDate = now.strftime(format)

    fileYear = fileDate[6:8]
    fileMonth = fileDate[3:5]
    fileDay = fileDate[0:2]

    channel= "D01"
    locatie = "NIV5"
    vmin = 60 #dB
    vmax = 120 #dB

    # LAeq file
    fileNameLAeq = "L%s%s%s.%s" % (fileDay, fileMonth, fileYear, channel)
    fileLAeq = open("c:/audiometing/%s" % (fileNameLAeq), "rb")

    # Terts file
    fileNameTerts = "T%s%s%s.%s" % (fileDay, fileMonth, fileYear, channel)
    fileTerts = open("c:/audiometing/%s" % (fileNameTerts), "rb")


    def readBinaryFile(file, zeroToVal):
        numbers = []
        byte = file.read(1)
        while byte:
            numbers.append(int.from_bytes(byte, "little"))
            if numbers[len(numbers)-1] == 0 and len(numbers) > 0 and zeroToVal == True:
                numbers[len(numbers)-1] = numbers[len(numbers)-2]
            byte = file.read(2)
        return numbers


    # ReadLAeq
    LAeq = np.array(readBinaryFile(fileLAeq, True))/10
    lengthLAeq = len(LAeq)

    # ReadTerts
    Terts = np.array(readBinaryFile(fileTerts, False))/10
    lengthTerts = int(len(Terts)/33)
    Terts = np.reshape(Terts, (lengthTerts, 33))
    Terts = Terts.T
    Terts[Terts > 150] = 0

    # frequencies
    yTerts = [20, 25, 31, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800,
            1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000]

    # cereate datetime array
    xLAeq = [datetime.datetime(int(fileYear), int(fileMonth), int(
        fileDay)) + datetime.timedelta(seconds=i) for i in range(lengthLAeq)]
    xTerts = [datetime.datetime(int(fileYear), int(fileMonth), int(
        fileDay)) + datetime.timedelta(seconds=i) for i in range(lengthTerts)]
    # Meshgrid for Terts
    XTerts, YTerts = np.meshgrid(xTerts, yTerts)

    # PLOTTEN
    fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, figsize=(20, 15))
    # PLOT LAEQ - D01
    ax1.plot(xLAeq, LAeq, linewidth=0.2)
    ax1.set(xlabel='Tijd', ylabel='LAeq (dBA)', title="%s - %s %s/%s/%s" %
            (locatie, now.strftime("%a"),fileDay, fileMonth, fileYear))
    ax1.set_xlim((xLAeq[0], xLAeq[-1]+datetime.timedelta(seconds=1)))
    ax1.set_ylim((vmin, vmax))
    date_form = DateFormatter("%H:%M")
    ax1.xaxis.set_major_formatter(date_form)
    ax1.grid(color='black', linestyle='--', linewidth=0.1)
    # PLOT TERTS
 
    cs = ax2.contourf(
        XTerts, YTerts, Terts[0:31], 30, vmin=vmin, vmax=vmax, cmap="turbo")
    #cbar = plt.colorbar(cs)
    ax2.set(xlabel='', ylabel='Hz (dB)')
    ax2.set_yscale('log')
    ax2.xaxis.set_major_formatter(date_form)

    channel= "D02"
    locatie = "Blaaslucht"
    vmin = 60 #dB
    vmax = 140 #dB

    # LAeq file
    fileNameLAeq = "L%s%s%s.%s" % (fileDay, fileMonth, fileYear, channel)
    fileLAeq = open("c:/audiometing/%s" % (fileNameLAeq), "rb")

    # Terts file
    fileNameTerts = "T%s%s%s.%s" % (fileDay, fileMonth, fileYear, channel)
    fileTerts = open("c:/audiometing/%s" % (fileNameTerts), "rb")


    def readBinaryFile(file, zeroToVal):
        numbers = []
        byte = file.read(1)
        while byte:
            numbers.append(int.from_bytes(byte, "little"))
            if numbers[len(numbers)-1] == 0 and len(numbers) > 0 and zeroToVal == True:
                numbers[len(numbers)-1] = numbers[len(numbers)-2]
            byte = file.read(2)
        return numbers


    # ReadLAeq
    LAeq = np.array(readBinaryFile(fileLAeq, True))/10
    lengthLAeq = len(LAeq)

    # ReadTerts
    Terts = np.array(readBinaryFile(fileTerts, False))/10
    lengthTerts = int(len(Terts)/33)
    Terts = np.reshape(Terts, (lengthTerts, 33))
    Terts = Terts.T
    Terts[Terts > 150] = 0

    # frequencies
    yTerts = [20, 25, 31, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800,
            1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000]

    # cereate datetime array
    xLAeq = [datetime.datetime(int(fileYear), int(fileMonth), int(
        fileDay)) + datetime.timedelta(seconds=i) for i in range(lengthLAeq)]
    xTerts = [datetime.datetime(int(fileYear), int(fileMonth), int(
        fileDay)) + datetime.timedelta(seconds=i) for i in range(lengthTerts)]
    # Meshgrid for Terts
    XTerts, YTerts = np.meshgrid(xTerts, yTerts)

    # PLOT LAEQ - D02
    ax3.plot(xLAeq, LAeq+25, linewidth=0.2)
    ax3.set(xlabel='Tijd', ylabel='LAeq (dBA)', title="%s - %s %s/%s/%s" %
            (locatie, now.strftime("%a"),fileDay, fileMonth, fileYear))
    ax3.set_xlim((xLAeq[0], xLAeq[-1]+datetime.timedelta(seconds=1)))
    ax3.set_ylim((vmin, vmax))
    date_form = DateFormatter("%H:%M")
    ax3.xaxis.set_major_formatter(date_form)
    ax3.grid(color='black', linestyle='--', linewidth=0.1)
    # PLOT TERTS
 
    cs = ax4.contourf(
        XTerts, YTerts, Terts[0:31]+25, 30, vmin=vmin, vmax=vmax, cmap="turbo")
    #cbar = plt.colorbar(cs)
    ax4.set(xlabel='Tijd', ylabel='Hz (dB)')
    ax4.set_yscale('log')
    ax4.xaxis.set_major_formatter(date_form)
    fig.savefig("c:\\audiometing\%s%s%s-%s.png" % (fileYear, fileMonth, fileDay, now.strftime("%a")))

    #plt.show()

	
	
	
email = EmailSender(
    host='smtp.gmail.com',
    port=587,
    user_name="tractebel.monitoring@gmail.com",
    password="jhuj tvbb rwca jcho"
)

email.send(
    subject="Geluidsmeting - Umicore - %s %s-%s-%s " % (now.strftime("%a"),fileDay,fileMonth,fileYear),
    sender="tractebel.monitoring@gmail.com",
    receivers=['luc.schillemans@external.tractebel.engie.com','tom.hennebel@eu.umicore.com','jozef.hosteaux@eu.umicore.com'],
    html="""
        {{ myplot }}
    """,
    body_images={"myplot": fig}
)

plt.clf()
plt.close('all')
