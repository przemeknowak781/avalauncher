import math
def to_pl1992(lat, lon):
    a=6378137.0; f=1/298.257222101; e2=f*(2-f); k0=0.9992; lon0=math.radians(19.0)
    phi=math.radians(lat); lam=math.radians(lon)
    n=f/(2-f); A=a/(1+n)*(1+n*n/4+n**4/64)
    al=[None, n/2-2*n*n/3+5*n**3/16, 13*n*n/48-3*n**3/5, 61*n**3/240]
    t=math.sinh(math.atanh(math.sin(phi))-2*math.sqrt(n)/(1+n)*math.atanh(2*math.sqrt(n)/(1+n)*math.sin(phi)))
    xi=math.atan(t/math.cos(lam-lon0)); eta=math.atanh(math.sin(lam-lon0)/math.sqrt(1+t*t))
    N=A*(xi+sum(al[j]*math.sin(2*j*xi)*math.cosh(2*j*eta) for j in (1,2,3)))
    E=A*(eta+sum(al[j]*math.cos(2*j*xi)*math.sinh(2*j*eta) for j in (1,2,3)))
    return 500000+k0*E, -5300000+k0*N
if __name__=='__main__':
    for name,lat,lon in [('Krakow Rynek',50.0617,19.9373),('Kasprowy',49.2319,19.9817),('Hala Gas.',49.2440,20.0040)]:
        print(name, [round(v,1) for v in to_pl1992(lat,lon)])
