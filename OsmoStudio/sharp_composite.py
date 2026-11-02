"""Native-resolution projection with narrow seam blending to retain source detail."""
import cv2 as cv
import numpy as np
import math

def compose(images,stitcher):
 cameras=stitcher.cameras();work=stitcher.workScale()
 Ks=[]
 for c in cameras:
  K=c.K().astype(np.float32);K[0,:]/=work;K[1,:]/=work;Ks.append(K)
 focal=float(np.median([c.focal/work for c in cameras]))
 seam_scale=min(1.,math.sqrt(1_000_000/max(im.shape[0]*im.shape[1] for im in images)))
 small_warper=cv.PyRotationWarper('spherical',focal*seam_scale)
 small_images=[];small_masks=[];small_corners=[]
 for im,K,c in zip(images,Ks,cameras):
  size=(round(im.shape[1]*seam_scale),round(im.shape[0]*seam_scale));small=cv.resize(im,size,interpolation=cv.INTER_AREA)
  k=K.copy();k[0,:]*=seam_scale;k[1,:]*=seam_scale
  corner,warped=small_warper.warp(small,k,c.R,cv.INTER_LINEAR,cv.BORDER_REFLECT)
  _,mask=small_warper.warp(np.full(small.shape[:2],255,np.uint8),k,c.R,cv.INTER_NEAREST,cv.BORDER_CONSTANT)
  small_images.append(warped);small_masks.append(mask);small_corners.append(corner)
 compensator=cv.detail.ExposureCompensator_createDefault(cv.detail.ExposureCompensator_GAIN_BLOCKS)
 compensator.feed(small_corners,small_images,small_masks)
 seam_masks=[cv.UMat(m.copy()) for m in small_masks]
 cv.detail.GraphCutSeamFinder('COST_COLOR_GRAD').find([im.astype(np.float32) for im in small_images],small_corners,seam_masks)
 warper=cv.PyRotationWarper('spherical',focal)
 rois=[warper.warpRoi((im.shape[1],im.shape[0]),K,c.R) for im,K,c in zip(images,Ks,cameras)]
 x=min(r[0] for r in rois);y=min(r[1] for r in rois);right=max(r[0]+r[2] for r in rois);bottom=max(r[1]+r[3] for r in rois)
 blender=cv.detail.MultiBandBlender();blender.setNumBands(2);blender.prepare((x,y,right-x,bottom-y))
 # Keep real source pixels to cover any rounding-sized gaps at seam junctions.
 fallback=np.zeros((bottom-y,right-x,3),np.uint8);coverage=np.zeros((bottom-y,right-x),np.uint8)
 for i,(im,K,c) in enumerate(zip(images,Ks,cameras)):
  corner,warped=warper.warp(im,K,c.R,cv.INTER_CUBIC,cv.BORDER_REFLECT)
  _,mask=warper.warp(np.full(im.shape[:2],255,np.uint8),K,c.R,cv.INTER_NEAREST,cv.BORDER_CONSTANT)
  compensator.apply(i,corner,warped,mask)
  seam=cv.resize(seam_masks[i].get(),(warped.shape[1],warped.shape[0]),interpolation=cv.INTER_NEAREST)
  radius=int(math.ceil(1/seam_scale))
  seam=cv.dilate(seam,np.ones((2*radius+1,2*radius+1),np.uint8));seam=cv.bitwise_and(seam,mask)
  ox,oy=corner[0]-x,corner[1]-y;hh,ww=mask.shape
  target=fallback[oy:oy+hh,ox:ox+ww];known=coverage[oy:oy+hh,ox:ox+ww]
  take=(known==0)&(mask>0);target[take]=warped[take];known[mask>0]=255
  blender.feed(warped.astype(np.int16),seam,corner)
  print(f'Details zusammensetzen {i+1}/{len(images)}',flush=True)
 result,mask=blender.blend(None,None)
 result=np.clip(result,0,255).astype(np.uint8)
 holes=(mask==0)&(coverage>0);result[holes]=fallback[holes];result[coverage==0]=0
 print(f'Naht-Lücken mit Originalpixeln geschlossen: {int(holes.sum())}',flush=True)
 return result
