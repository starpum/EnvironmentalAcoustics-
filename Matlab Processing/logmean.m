function L_mean = logmean(L1,varargin)
    if nargin>1
        axis = varargin{1};
    else
        axis = 1;
    end
    
    hulp = 10.^(L1/10);
    hulp = mean(hulp,axis,'omitnan');
    L_mean = 10*log10(hulp);
end