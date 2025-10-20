mapnaam = './Meetbestanden Referentie';

files = dir(mapnaam);
files = files(3:end);

index_start = 0;
for par2 = 1:numel(files)
    disp([num2str(round((par2-1)/numel(files)*100)) '%'])
    %% Setup the Import Options
    opts = spreadsheetImportOptions("NumVariables", 39);

    % Specify sheet and range
    opts.Sheet = "Lfeq";
    opts.DataRange = "A10:AM86407";

    % Specify column names and types
    opts.VariableNames = ["Period", "Time", "VarName3", "Hz", "Hz1", "Hz2", "Hz3", "Hz4", "Hz5", "Hz6", "Hz7", "Hz8", "Hz9", "Hz10", "Hz11", "Hz12", "Hz13", "Hz14", "Hz15", "Hz16", "Hz17", "Hz18", "Hz19", "Hz20", "Hz21", "kHz", "kHz1", "kHz2", "kHz3", "kHz4", "kHz5", "kHz6", "kHz7", "kHz8", "kHz9", "kHz10", "kHz11", "kHz12", "kHz13"];
    opts.SelectedVariableNames = ["Period", "Time", "VarName3", "Hz", "Hz1", "Hz2", "Hz3", "Hz4", "Hz5", "Hz6", "Hz7", "Hz8", "Hz9", "Hz10", "Hz11", "Hz12", "Hz13", "Hz14", "Hz15", "Hz16", "Hz17", "Hz18", "Hz19", "Hz20", "Hz21", "kHz", "kHz1", "kHz2", "kHz3", "kHz4", "kHz5", "kHz6", "kHz7", "kHz8", "kHz9", "kHz10", "kHz11", "kHz12", "kHz13"];
    opts.VariableTypes = ["double", "string", "string", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double"];
    opts = setvaropts(opts, [2, 3], "WhitespaceRule", "preserve");
    opts = setvaropts(opts, [2, 3], "EmptyFieldRule", "auto");

    % Import the data
    data = readtable([mapnaam '/' files(par2).name], opts, "UseExcel", false);

    %%
    % Geluidsdrukniveaus
    Lpz = table2array(data(:,9:end));

    % index
    index = (1:size(Lpz,1)).'+index_start;

    % Datum
    starttijd = char(data{:,2});
    slash = starttijd(:,1);
    for par1=1:numel(slash)
        slash(par1) = '/';
    end
    spatie = starttijd(:,12);
    datum = [starttijd(:,10:11),slash,starttijd(:,7:8),slash,starttijd(:,2:5),spatie,starttijd(:,13:20)];
    datum = string(datum);

    % A-gewogen waarde
    f = [20 25 31.5 40 50 63 80 100 125 160 200 250 315 400 500 630 800 1000 1250 1600 2000 2500 3150 4000 5000 6300 8000 10000 12500 16000 20000];
    LpA = Lpz + acorr(f);
    Total_A = logsum(LpA,2);
    Total_C = zeros(size(Total_A));
    Total_Z = Total_C;
    overload = Total_C;

    %%
    index(isinf(Total_A),:)=[];
    datum(isinf(Total_A),:)=[];
    Lpz(isinf(Total_A),:)=[];
    Total_C(isinf(Total_A),:)=[];
    Total_Z(isinf(Total_A),:)=[];
    overload(isinf(Total_A),:)=[];
    Total_A(isinf(Total_A),:)=[];
       
    tabel = table(index,datum,Total_A,Lpz,Total_A,Total_C,Total_Z,overload);
    writetable(tabel,['hulpfile_' num2str(par2) '.txt'],'Delimiter','\t','WriteVariableNames', 0)
    
    index_start = max(index);
    
    %%
    a = figure;
    a.Position=[100 100 1500 500];
    hulp = [];
    n = floor(numel(Lpz(:,1))/60);
    for par1=1:numel(f)
        hulp(par1,:) = logmean(reshape(Lpz(1:n*60,par1),60,n),1).';
    end
    pcolor(index(1:60:n*60),f,hulp);
    set(gca,'yscale','log')
    shading interp
    yticks(f(3:3:end))
    xticks(index(1:1800:end))
    
    %datum = datestr(datetime(datum,'Format','dd/MM/uuuu HH:mm:ss')-51,'dd/mm/yyyy HH:MM:ss');
    
    
    xticklabels(datum(1:1800:end,:))
    xtickangle(45)
    colormap jet
    title('meting Total Referentie - spectrogram minuutwaarden')
    ylabel('f[Hz]')
    
    hold on
    for par3=3:3:numel(f)
        plot3([index(1),index(end)],f(par3)*[1,1],[1,1],'k-')
    end
    
    saveas(gcf,['Spectrogram_' files(par2).name(17:end-13)],'png')
    close all
end

code = 'copy basisfile_svantek.txt';
for par2 = 1:numel(files)
    code = [code '+hulpfile_' num2str(par2) '.txt'];
end
code = [code ' dagfile.txt'];
system(code)

