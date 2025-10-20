function L_sum = logsum(L1,varargin)
    if nargin>1
        axis = varargin{1};
    else
        axis = 1;
    end
    
    hulp = 10.^(L1/10);
    hulp = sum(hulp,axis,'omitnan');
    L_sum = 10*log10(hulp);
end