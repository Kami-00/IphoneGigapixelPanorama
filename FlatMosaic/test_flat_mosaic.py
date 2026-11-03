import tempfile,unittest
from pathlib import Path
import numpy as np,cv2 as cv
from flat_mosaic import mosaic,features,pair_matches,chain,refine,largest_rect,boxes,project,grid_neighbours

def wall(w=1100,h=1300,seed=7):
    """A flat subject with enough distinct detail to register honestly."""
    rng=np.random.default_rng(seed);im=np.full((h,w,3),28,np.uint8)
    for _ in range(90):
        x,y=rng.integers(0,w-90),rng.integers(0,h-120);c=tuple(int(v) for v in rng.integers(60,255,3))
        cv.rectangle(im,(x,y),(x+int(rng.integers(50,90)),y+int(rng.integers(70,120))),c,-1)
        cv.putText(im,f'{rng.integers(100,999)}',(x+6,y+40),cv.FONT_HERSHEY_SIMPLEX,.7,(250,250,250),2,cv.LINE_AA)
        cv.circle(im,(x+30,y+70),int(rng.integers(6,16)),tuple(int(v) for v in rng.integers(0,255,3)),-1)
    return cv.GaussianBlur(im,(0,0),.6)

def tiles(scene,folder,size=(620,720),origins=((0,0),(300,0),(0,420),(300,420)),jitter=9,seed=3):
    """Overlapping views of the wall, each with its own slight perspective."""
    rng=np.random.default_rng(seed);paths=[];truth=[]
    for n,(ox,oy) in enumerate(origins):
        w,h=size;src=np.float32([[ox,oy],[ox+w,oy],[ox+w,oy+h],[ox,oy+h]])
        dst=np.float32([[0,0],[w,0],[w,h],[0,h]])+rng.uniform(-jitter,jitter,(4,2)).astype(np.float32)
        H=cv.getPerspectiveTransform(src,dst)
        p=Path(folder)/f'tile{n}.png';cv.imwrite(str(p),cv.warpPerspective(scene,H,(w,h),flags=cv.INTER_CUBIC))
        paths.append(p);truth.append(H)
    return paths,truth

class MosaicTests(unittest.TestCase):
    def test_pair_transform_matches_the_truth(self):
        scene=wall()
        with tempfile.TemporaryDirectory() as d:
            paths,truth=tiles(scene,d,origins=((0,0),(300,0)))
            kps,dess,sizes,s=features(paths,2400,12000)
            self.assertEqual(s,1.)
            pairs=pair_matches(kps,dess)
            self.assertIn((0,1),pairs)
            ref,Hs=chain(pairs,2);Hs,fit=refine(Hs,pairs,ref,2)
            # Both frames must land on the same scene point, to well under a pixel.
            probe=np.float64([[150,180],[400,300],[520,640]])
            a=project(np.linalg.inv(truth[0]),probe);b=project(truth[1],a)
            self.assertLess(np.abs(project(Hs[0],probe)-project(Hs[1],b)).max(),1.5)
            self.assertLess(fit['rms_after'],1.5)

    def test_mosaic_rebuilds_the_scene(self):
        scene=wall()
        with tempfile.TemporaryDirectory() as d:
            paths,_=tiles(scene,d)
            out=Path(d)/'Mosaik.png';report=mosaic([str(p) for p in paths],out,work=Path(d)/'arbeit')
            self.assertTrue(out.exists());self.assertTrue(out.with_suffix('.json').exists())
            result=cv.imread(str(out))
            self.assertEqual(report['frames_used'],4)
            # A cropped result carries no uncovered pixels at all.
            self.assertEqual(report['uncovered_pixels'],0)
            self.assertLess((result.sum(axis=2)==0).mean(),.001)
            # The composite must still contain the real artwork, not a smeared average.
            patch=scene[500:620,420:560]
            score=cv.matchTemplate(result,patch,cv.TM_CCOEFF_NORMED).max()
            self.assertGreater(score,.9)

    def test_full_canvas_keeps_more_than_the_crop(self):
        scene=wall()
        with tempfile.TemporaryDirectory() as d:
            paths,_=tiles(scene,d)
            small=mosaic([str(p) for p in paths],Path(d)/'a.png',work=Path(d)/'w')
            whole=mosaic([str(p) for p in paths],Path(d)/'b.png',crop=False,work=Path(d)/'w')
            self.assertGreater(whole['width']*whole['height'],small['width']*small['height'])
            self.assertGreater(whole['uncovered_pixels'],0)

    def test_reused_calibration_still_reports_its_alignment(self):
        scene=wall()
        with tempfile.TemporaryDirectory() as d:
            paths,_=tiles(scene,d);cal=Path(d)/'kal.json'
            first=mosaic([str(p) for p in paths],Path(d)/'a.png',work=Path(d)/'w',calibration=cal)
            self.assertTrue(cal.exists())
            again=mosaic([str(p) for p in paths],Path(d)/'b.png',work=Path(d)/'w',calibration=cal)
            self.assertEqual(again['alignment']['reused'],str(cal))
            for key in ('reference','rms_after','used_pairs','dropped_pairs'):
                self.assertEqual(again['alignment'][key],first['alignment'][key])
            self.assertEqual((again['width'],again['height']),(first['width'],first['height']))

    def test_wrong_pair_is_dropped_but_connection_kept(self):
        rng=np.random.default_rng(11);pts=rng.uniform(0,600,(220,2))
        # Frame 1 sits 50 px further along, so its transform shifts points back by +50.
        truth=[np.eye(3),np.array([[1.,0,50],[0,1.,0],[0,0,1.]]),np.array([[1.,0,100],[0,1.,0],[0,0,1.]])]
        pairs={(0,1):(pts,pts-[50,0]),(1,2):(pts,pts-[50,0]),(0,2):(pts,pts+[480,370])}
        Hs,fit=refine([h.copy() for h in truth],pairs,0,3)
        self.assertIn([0,2],fit['dropped_pairs'])
        self.assertEqual(fit['used_pairs'],[[0,1],[1,2]])
        self.assertLess(fit['rms_after'],1.)

    def test_capture_pattern_names_the_right_neighbours(self):
        g=grid_neighbours(14,7,2,'serpentine')
        self.assertEqual(len(g),31)
        for pair in [(0,1),(5,6),(7,8),(12,13)]:self.assertIn(pair,g)   # entlang der Reihen
        for pair in [(6,7),(0,13),(3,10)]:self.assertIn(pair,g)         # Wende und Senkrechte
        for pair in [(0,7),(0,6),(2,5)]:self.assertNotIn(pair,g)        # liegen nicht nebeneinander
        raster=grid_neighbours(14,7,2,'raster')
        self.assertIn((0,7),raster);self.assertNotIn((0,13),raster)
        with self.assertRaises(ValueError):grid_neighbours(14,3,2)
        with self.assertRaises(ValueError):grid_neighbours(4,2,2,'zickzack')

    def test_matching_stays_inside_the_pattern(self):
        scene=wall()
        with tempfile.TemporaryDirectory() as d:
            paths,_=tiles(scene,d)
            kps,dess,sizes,s=features(paths,2400,12000)
            allowed={(0,1),(1,3)}
            self.assertTrue(set(pair_matches(kps,dess,allowed=allowed))<=allowed)
            self.assertGreater(len(pair_matches(kps,dess)),2)

    def test_largest_rect_finds_the_filled_block(self):
        cov=np.zeros((120,140),np.uint8);cov[10:90,20:100]=255;cov[95:110,0:140]=255
        x,y,w,h=largest_rect(cov,inset=2)
        self.assertTrue(20<=x<=24 and 10<=y<=14)
        self.assertTrue(70<=w<=78 and 70<=h<=78)

    def test_boxes_follow_the_output_scale(self):
        H=[np.eye(3)];full=boxes(H,[(800,600)],1.)[0];half=boxes(H,[(800,600)],.5)[0]
        self.assertEqual((full[3]-full[1],full[4]-full[2]),(800,600))
        self.assertEqual((half[3]-half[1],half[4]-half[2]),(400,300))

    def test_unrelated_images_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            for n,seed in enumerate((1,99)):cv.imwrite(str(Path(d)/f'x{n}.png'),wall(620,720,seed))
            with self.assertRaises(RuntimeError):
                mosaic([str(Path(d)/'x0.png'),str(Path(d)/'x1.png')],Path(d)/'o.png',work=Path(d)/'w')
            self.assertFalse((Path(d)/'o.png').exists())

    def test_single_input_rejected_before_any_work(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'one.png';cv.imwrite(str(p),wall(400,400))
            with self.assertRaises(ValueError):mosaic([str(p)],Path(d)/'o.png',work=Path(d)/'w')
            self.assertFalse((Path(d)/'o.png').exists())

if __name__=='__main__':unittest.main()
