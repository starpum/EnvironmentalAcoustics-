clear all; close all;

foldername = './Datas';

files = dir(foldername);
files = files(3:end);

index_start = 0;
for par2 = 1:numel(files)
    
    disp([num2str(round((par2-1)/numel(files)*100)) '%'])
     % Setup the Import Options
    opts = spreadsheetImportOptions("NumVariables", 19);

    % Specify sheet and range
    opts.Sheet = "Lfeq";
    opts.DataRange = "A10:S2000";

    % Specify column names and types 
    
    opts.VariableNames = ["Period", "Time", "VarName3", "Hz", "Hz1", "Hz2", "Hz3", "Hz4", "Hz5", "Hz6", "Hz7", "Hz8", "Hz9", "Hz10", "kHz1", "kHz2", "kHz3", "kHz4", "kHz5"];
    opts.SelectedVariableNames = ["Period", "Time", "VarName3", "Hz", "Hz1", "Hz2", "Hz3", "Hz4", "Hz5", "Hz6", "Hz7", "Hz8", "Hz9", "Hz10" "kHz1", "kHz2", "kHz3", "kHz4", "kHz5"];
    opts.VariableTypes = ["double", "string", "string", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double", "double"];
    
    opts = setvaropts(opts, [2, 3], "WhitespaceRule", "preserve");
    opts = setvaropts(opts, [2, 3], "EmptyFieldRule", "auto");

    % Import the data
    data = readtable([foldername '/' files(par2).name], opts, "UseExcel", false);

    % Create data table
    Acc = table2array(data(:,4:13));
    N = size(Acc);
    N = N(2);

    % index
    index = (1:size(Acc,1)).'+index_start;

    % Create date time entry
    startdate = char(data{:,2});
    slash = startdate(:,1);
    for par1=1:numel(slash)
        slash(par1) = '/';
    end
    space = startdate(:,10);
    datum = [startdate(:,10:11),slash,startdate(:,7:8),slash,startdate(:,2:5),space,startdate(:,13:20)];
    datum = string(datum);

    % Return to displacement 
    %f = [0.5 1 2 4 8 16 31.5 63 125 250 500 1000 2000 4000 8000 16000];
    f = [0.5 1 2 4 8 16 31.5 63];
    w = 2*pi*f;

    for par3 = 1:numel(f)
        Disp(:,par3) = Acc(:,par3)./w(par3); %displacement is acc / angular freq 
        Vel(:,par3) = Disp(:,par3)./w(par3); %Velocity is displacement / angular freq
    end

    Total_Acc = logsum(Acc,2);


    % Plot acceleration datas 

    figure(par2)
    legendCell = cellstr(num2str(f'));
    xticks(index(1:300:end))
    xticklabels(datum(1:300:end))
    xtickangle(45)
    colormap jet
    title('Acceleration')
    xlabel('date&time')
    ylabel('A [m/s-2]')
    hold on
    for i = 1:N
        plot((10^-3)*Acc(:,i));
    end
    legend(legendCell);
    hold off

    % Plot displacement datas 

    % legendCell = cellstr(num2str(f'));
    % xticks(index(1:300:end))
    % xticklabels(datum(1:300:end))
    % xtickangle(45)
    % colormap jet
    % title('Displacement')
    % xlabel('date&time')
    % ylabel('x [m]')
    % hold on
    % subplot(2,1,2)
    % for i = 1:length(Disp)
    %     plot((10^-3)*Disp(:,i));
    % end
    % legend(legendCell);
    % hold off
end 
