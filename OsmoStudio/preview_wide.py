from pathlib import Path
import numpy as np,cv2 as cv,json,sys,math
folder=Path(sys.argv[1]);cal=json.loads((folder/'360-Kalibrierung.json').read_text());W,H=2048,1024
lon=np.linspace(-math.pi,math.pi,W,endpoint=False,dtype=np.float32)[None,:];theta=np.linspace(0,math.pi,H,endpoint=False,dtype=np.float32)[:,None]
rx=np.sin(theta)*np.sin(lon);ry=-np.cos(theta);rz=np.sin(theta)*np.cos(lon);best=np.full((H,W),-1.,np.float32);result=np.zeros((H,W,3),np.uint8)
for index,(file,k,r) in enumerate(zip(cal['files'],cal['K'],cal['R'])):
 path=folder/'360-Arbeitsdateien'/(Path(file).stem+'.npy');im=np.load(path,mmap_mode='r');scale=800/im.shape[1];src=cv.resize(im,None,fx=scale,fy=scale,interpolation=cv.INTER_AREA);K=np.array(k,np.float32);K[0,:]*=scale;K[1,:]*=scale;Rt=np.array(r,np.float32).T
 cz=Rt[2,0]*rx+Rt[2,1]*ry+Rt[2,2]*rz;cx=Rt[0,0]*rx+Rt[0,1]*ry+Rt[0,2]*rz;cy=Rt[1,0]*rx+Rt[1,1]*ry+Rt[1,2]*rz;z=np.where(cz>0,cz,1)
 mx=(K[0,0]*cx/z+K[0,2]).astype(np.float32);my=(K[1,1]*cy/z+K[1,2]).astype(np.float32);valid=(cz>0)&(mx>1)&(my>1)&(mx<src.shape[1]-2)&(my<src.shape[0]-2)
 take=valid&(cz>best);warped=cv.remap(src,mx,my,cv.INTER_LINEAR);result[take]=warped[take];best[take]=cz[take]
cv.imwrite(str(folder/'Geometrie-Vorschau.jpg'),result)
# Perspective views remove the expected distortion of the flat 2:1 sphere.
for yaw in [-140,-40,150]:
 w,h=1100,700;xx,yy=np.meshgrid((np.arange(w)-w/2)/(h/2),(np.arange(h)-h/2)/(h/2));zz=np.ones_like(xx);length=np.sqrt(xx*xx+yy*yy+zz*zz);xx/=length;yy/=length;zz/=length
 angle=math.radians(yaw);x=np.cos(angle)*xx+np.sin(angle)*zz;z=-np.sin(angle)*xx+np.cos(angle)*zz
 u=((np.arctan2(x,z)/(2*math.pi)+.5)*W).astype(np.float32);v=(np.arccos(np.clip(-yy,-1,1))/math.pi*H).astype(np.float32)
 cv.imwrite(str(folder/f'Pruefansicht-{yaw}.jpg'),cv.remap(result,u,v,cv.INTER_LINEAR,borderMode=cv.BORDER_WRAP))
print('Geometrievorschau erstellt')
